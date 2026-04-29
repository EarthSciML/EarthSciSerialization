"""mms_evaluator.py — 1D stencil walker kernels (esm-ga7).

Python parity slice of ``packages/EarthSciSerialization.jl/src/mms_evaluator.jl``
covering the pieces RFC §5.2.8 needs to honour ``ghost_width`` and
``boundary_policy`` on a discretization rule:

- :func:`apply_stencil_periodic_1d` — wrap-around 1D stencil walker.
- :func:`apply_stencil_ghosted_1d` — interior-only walker with ghost-cell
  synthesis driven by the rule's ``boundary_policy``. Closed-set kinds
  ``periodic``, ``reflecting``, ``one_sided_extrapolation`` and
  ``prescribed`` (plus the v0.3.x aliases ``ghosted`` / ``neumann_zero`` /
  ``extrapolate``) are evaluated. ``panel_dispatch`` parses but raises
  ``E_GHOST_FILL_UNSUPPORTED`` (cubed-sphere panel-boundary distance
  switching is tracked under esm-4el).

The full MMS convergence harness (registry, ``mms_convergence``, latlon /
WENO / MPAS variants) is not yet ported to Python — only the kernel that
the walker needs.
"""

from __future__ import annotations

from typing import Any, Callable, List, Mapping, Optional, Tuple, Union

import numpy as np

from .expression import evaluate
from .parse import _parse_expression


class MMSEvaluatorError(Exception):
    """Stable-coded error raised by the walker kernels.

    Recognised codes (mirror the Julia binding):

    - ``E_MMS_BAD_FIXTURE``         — stencil entry / argument shape invalid.
    - ``E_GHOST_WIDTH_TOO_SMALL``   — declared ghost_width < max |offset|.
    - ``E_GHOST_FILL_UNSUPPORTED``  — boundary_policy kind parses but is not
      evaluated by the 1D walker (currently: ``panel_dispatch``).
    """

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


BOUNDARY_POLICY_KINDS: Tuple[str, ...] = (
    "periodic", "reflecting", "one_sided_extrapolation", "prescribed",
    "ghosted", "neumann_zero", "extrapolate", "panel_dispatch",
)

_BOUNDARY_POLICY_ALIASES = {
    "ghosted": "prescribed",
    "neumann_zero": "reflecting",
    "extrapolate": "one_sided_extrapolation",
}


def _canonical_boundary_kind(k: str) -> str:
    return _BOUNDARY_POLICY_ALIASES.get(k, k)


def eval_coeff(node: Any, bindings: Mapping[str, float]) -> float:
    """Evaluate a JSON-decoded stencil ``coeff`` node against ``bindings``.

    Thin wrapper over :func:`earthsci_toolkit.parse._parse_expression`
    followed by :func:`earthsci_toolkit.expression.evaluate`. ``node`` is a
    raw JSON value — a number, a bare-identifier string, or an
    ``{op, args, ...}`` dict.
    """

    expr = _parse_expression(node)
    return float(evaluate(expr, dict(bindings)))


def _resolve_substencil(stencil_json: Any,
                        sub_stencil: Optional[str]) -> List[Any]:
    """Resolve a stencil spec (list-form or multi-output dict-form).

    A bare list is returned as-is. A ``Mapping`` is treated as a
    sub-stencil-keyed multi-output rule (PPM-style) and the caller MUST
    select one via ``sub_stencil``.
    """

    if isinstance(stencil_json, Mapping):
        if sub_stencil is None:
            raise MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "rule has multi-stencil mapping; input.esm must select one "
                f"via `sub_stencil` (available: {list(stencil_json.keys())})",
            )
        if sub_stencil not in stencil_json:
            raise MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                f"rule has no sub-stencil {sub_stencil!r} "
                f"(available: {list(stencil_json.keys())})",
            )
        return list(stencil_json[sub_stencil])
    if sub_stencil is not None:
        raise MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            f"`sub_stencil={sub_stencil!r}` was requested but rule carries "
            "a single stencil list, not a multi-stencil mapping",
        )
    return list(stencil_json)


def apply_stencil_periodic_1d(stencil_json: Any,
                              u: Any,
                              bindings: Mapping[str, float],
                              *,
                              sub_stencil: Optional[str] = None) -> np.ndarray:
    """Apply a 1D Cartesian stencil to ``u`` with wrap-around periodicity.

    Each entry of ``stencil_json`` carries ``selector.offset`` (int) and a
    ``coeff`` AST node. Coefficients are evaluated once per call against
    ``bindings``. The result is a length-``n`` ``numpy.ndarray``.

    ``stencil_json`` may also be a multi-stencil mapping; pass
    ``sub_stencil`` to select which named entry to apply.
    """

    entries = _resolve_substencil(stencil_json, sub_stencil)
    u_arr = np.asarray(u, dtype=np.float64)
    n = u_arr.shape[0]
    coeff_pairs: List[Tuple[int, float]] = []
    for s in entries:
        sel = s["selector"]
        coeff_pairs.append((int(sel["offset"]), eval_coeff(s["coeff"], bindings)))
    out = np.zeros(n, dtype=np.float64)
    for i in range(n):
        acc = 0.0
        for off, c in coeff_pairs:
            j = (i + off) % n
            acc += c * u_arr[j]
        out[i] = acc
    return out


def apply_stencil_ghosted_1d(stencil_json: Any,
                             u: Any,
                             bindings: Mapping[str, float],
                             *,
                             ghost_width: int,
                             boundary_policy: Union[str, Mapping[str, Any]],
                             prescribe: Optional[Callable[[str, int], float]] = None,
                             degree: int = 1,
                             sub_stencil: Optional[str] = None) -> np.ndarray:
    """Apply a 1D stencil after extending ``u`` by ``ghost_width`` cells per side.

    The fill on each side is driven by ``boundary_policy`` (RFC §5.2.8):

    - ``"periodic"`` — wrap-around. Bit-equal to
      :func:`apply_stencil_periodic_1d` on identical inputs.
    - ``"reflecting"`` (alias ``"neumann_zero"``) — mirror across the
      boundary face: ghost cell ``k`` (1 = closest to the edge) equals
      interior cell ``k`` on the left and ``n − k + 1`` on the right.
    - ``"one_sided_extrapolation"`` (alias ``"extrapolate"``) — polynomial
      extrapolation from the interior. ``degree`` ∈ ``0..3``; default ``1``
      (linear). May also be supplied as ``boundary_policy.degree`` when the
      policy is given in spec-dict form.
    - ``"prescribed"`` (alias ``"ghosted"``) — caller supplies ghost values
      via ``prescribe(side, k)`` where ``side`` is ``"left"`` or ``"right"``
      and ``k ∈ 1..ghost_width`` (1 = closest to the boundary).

    ``ghost_width`` MUST be ≥ ``max(|offset|)`` across stencil entries; an
    underspecified ghost width raises
    :class:`MMSEvaluatorError` with code ``E_GHOST_WIDTH_TOO_SMALL``.

    ``panel_dispatch`` parses but raises ``E_GHOST_FILL_UNSUPPORTED``;
    cubed-sphere panel-boundary distance switching is tracked under
    esm-4el.
    """

    if ghost_width < 0:
        raise MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            f"ghost_width must be non-negative, got {ghost_width}",
        )
    entries = _resolve_substencil(stencil_json, sub_stencil)
    coeff_pairs: List[Tuple[int, float]] = []
    max_off = 0
    for s in entries:
        sel = s["selector"]
        off = int(sel["offset"])
        coeff_pairs.append((off, eval_coeff(s["coeff"], bindings)))
        ao = abs(off)
        if ao > max_off:
            max_off = ao
    if ghost_width < max_off:
        raise MMSEvaluatorError(
            "E_GHOST_WIDTH_TOO_SMALL",
            f"stencil offset {max_off} exceeds ghost_width {ghost_width}; "
            "rule must declare `ghost_width` >= max(|offset|)",
        )

    u_arr = np.asarray(u, dtype=np.float64)
    n = u_arr.shape[0]
    if n < 2:
        raise MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            "ghosted stencil application requires at least 2 interior cells; "
            f"got {n}",
        )
    Ng = ghost_width
    u_ext = np.empty(n + 2 * Ng, dtype=np.float64)
    u_ext[Ng:Ng + n] = u_arr

    raw_kind = _extract_policy_kind(boundary_policy)
    kind = _canonical_boundary_kind(raw_kind)
    extra_degree = _extract_policy_degree(boundary_policy, degree)

    if kind == "periodic":
        _fill_ghosts_periodic(u_ext, u_arr, Ng)
    elif kind == "reflecting":
        _fill_ghosts_reflecting(u_ext, u_arr, Ng)
    elif kind == "one_sided_extrapolation":
        _fill_ghosts_one_sided(u_ext, u_arr, Ng, extra_degree)
    elif kind == "prescribed":
        if prescribe is None:
            raise MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "boundary_policy=`prescribed` requires a `prescribe` callable; "
                "callable receives (side, k) with side in ('left', 'right') "
                "and 1 <= k <= ghost_width",
            )
        _fill_ghosts_prescribed(u_ext, Ng, prescribe)
    elif kind == "panel_dispatch":
        raise MMSEvaluatorError(
            "E_GHOST_FILL_UNSUPPORTED",
            "boundary_policy=`panel_dispatch` not implemented for the 1D walker "
            "(cubed-sphere only); see esm-4el follow-up for the 2D adapter",
        )
    else:
        valid = ", ".join(BOUNDARY_POLICY_KINDS)
        raise MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            f"unknown boundary_policy kind {kind!r}; expected one of: {valid}",
        )

    out = np.zeros(n, dtype=np.float64)
    for i in range(n):
        acc = 0.0
        for off, c in coeff_pairs:
            acc += c * u_ext[Ng + i + off]
        out[i] = acc
    return out


def _extract_policy_kind(bp: Union[str, Mapping[str, Any]]) -> str:
    if isinstance(bp, str):
        return bp
    if isinstance(bp, Mapping):
        if "kind" not in bp:
            raise MMSEvaluatorError(
                "E_MMS_BAD_FIXTURE",
                "boundary_policy spec object must carry a `kind` field; "
                f"got keys {list(bp.keys())}",
            )
        return str(bp["kind"])
    raise MMSEvaluatorError(
        "E_MMS_BAD_FIXTURE",
        "boundary_policy must be a string or spec dict, "
        f"got {type(bp).__name__}",
    )


def _extract_policy_degree(bp: Union[str, Mapping[str, Any]],
                           default: int) -> int:
    if isinstance(bp, Mapping):
        raw = bp.get("degree")
        if raw is None:
            return default
        return int(raw)
    return default


def _fill_ghosts_periodic(u_ext: np.ndarray, u: np.ndarray, Ng: int) -> None:
    n = u.shape[0]
    for k in range(1, Ng + 1):
        u_ext[Ng - k] = u[n - k]
        u_ext[Ng + n + k - 1] = u[k - 1]


def _fill_ghosts_reflecting(u_ext: np.ndarray, u: np.ndarray, Ng: int) -> None:
    n = u.shape[0]
    for k in range(1, Ng + 1):
        u_ext[Ng - k] = u[k - 1]
        u_ext[Ng + n + k - 1] = u[n - k]


def _fill_ghosts_one_sided(u_ext: np.ndarray, u: np.ndarray,
                           Ng: int, degree: int) -> None:
    if not (0 <= degree <= 3):
        raise MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            f"one_sided_extrapolation degree must be in 0..3, got {degree}",
        )
    n = u.shape[0]
    if n <= degree:
        raise MMSEvaluatorError(
            "E_MMS_BAD_FIXTURE",
            f"one_sided_extrapolation degree {degree} requires at least "
            f"{degree + 1} interior cells; got {n}",
        )
    for k in range(1, Ng + 1):
        u_ext[Ng - k] = _extrapolate_left(u, degree, k)
        u_ext[Ng + n + k - 1] = _extrapolate_right(u, degree, k)


def _extrapolate_left(u: np.ndarray, degree: int, k: int) -> float:
    K = float(k)
    if degree == 0:
        return float(u[0])
    if degree == 1:
        return float(u[0]) + K * (float(u[0]) - float(u[1]))
    if degree == 2:
        return ((1.0 + 1.5 * K + 0.5 * K * K) * float(u[0])
                + (-2.0 * K - K * K) * float(u[1])
                + (0.5 * K + 0.5 * K * K) * float(u[2]))
    # degree == 3
    return ((1.0 + (11.0 / 6.0) * K + K * K + (1.0 / 6.0) * K ** 3) * float(u[0])
            + (-3.0 * K - 2.5 * K * K - 0.5 * K ** 3) * float(u[1])
            + (1.5 * K + 2.0 * K * K + 0.5 * K ** 3) * float(u[2])
            + ((-1.0 / 3.0) * K - 0.5 * K * K - (1.0 / 6.0) * K ** 3) * float(u[3]))


def _extrapolate_right(u: np.ndarray, degree: int, k: int) -> float:
    K = float(k)
    n = u.shape[0]
    if degree == 0:
        return float(u[n - 1])
    if degree == 1:
        return float(u[n - 1]) + K * (float(u[n - 1]) - float(u[n - 2]))
    if degree == 2:
        return ((1.0 + 1.5 * K + 0.5 * K * K) * float(u[n - 1])
                + (-2.0 * K - K * K) * float(u[n - 2])
                + (0.5 * K + 0.5 * K * K) * float(u[n - 3]))
    return ((1.0 + (11.0 / 6.0) * K + K * K + (1.0 / 6.0) * K ** 3) * float(u[n - 1])
            + (-3.0 * K - 2.5 * K * K - 0.5 * K ** 3) * float(u[n - 2])
            + (1.5 * K + 2.0 * K * K + 0.5 * K ** 3) * float(u[n - 3])
            + ((-1.0 / 3.0) * K - 0.5 * K * K - (1.0 / 6.0) * K ** 3) * float(u[n - 4]))


def _fill_ghosts_prescribed(u_ext: np.ndarray, Ng: int,
                            prescribe: Callable[[str, int], float]) -> None:
    n_interior = u_ext.shape[0] - 2 * Ng
    for k in range(1, Ng + 1):
        u_ext[Ng - k] = float(prescribe("left", k))
        u_ext[Ng + n_interior + k - 1] = float(prescribe("right", k))
