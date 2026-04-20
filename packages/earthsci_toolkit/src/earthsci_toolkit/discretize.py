"""RFC §12 DAE binding contract for Python (``earthsci_toolkit``).

The Python binding's strategy is **trivial-factor + error otherwise**:

* Algebraic equations whose LHS is a bare variable name and whose RHS
  does not reference that variable (transitively) are eliminated by
  symbolic substitution into every downstream equation. This covers
  the common observed-equation pattern (e.g. ``y = x^2``).
* Any residual algebraic equation — cyclic trivial factors, or an LHS
  that is not a bare variable (e.g. the unit-circle constraint
  ``x^2 + y^2 = 1``) — raises :class:`DiscretizationError` with code
  ``E_NONTRIVIAL_DAE``. The message names the offending equation(s),
  points to the Julia binding for full DAE support, and cites RFC §12.

With ``dae_support=False`` (or env ``ESM_DAE_SUPPORT=0``), no factoring
is attempted; any algebraic equation raises ``E_NO_DAE_SUPPORT`` — this
mirrors the Julia contract so callers can gate the binding behavior
uniformly.

Only the DAE classification + trivial-factor pass is implemented here;
the full §11 rewrite pipeline (rule engine, canonicalization, PDE-op
scan) is a parallel follow-up in this binding.
"""

from __future__ import annotations

import copy
import os
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


class DiscretizationError(Exception):
    """Error raised by :func:`discretize`.

    ``code`` is one of the RFC §12 stable error codes:

    - ``E_NO_DAE_SUPPORT`` — algebraic equations present with
      ``dae_support=False``.
    - ``E_NONTRIVIAL_DAE`` — algebraic equations remained after the
      trivial-factor pass (cyclic or non-``var ~ expr`` form).
    """

    def __init__(self, code: str, message: str):
        super().__init__(f"DiscretizationError({code}): {message}")
        self.code = code
        self.message = message


def discretize(
    esm: Dict[str, Any],
    *,
    dae_support: Optional[bool] = None,
) -> Dict[str, Any]:
    """Apply the RFC §12 DAE binding contract to an ESM document.

    The input is a parsed ESM payload as a ``dict`` (the form produced
    by :func:`json.loads` on an ``.esm`` file). The input is not
    mutated; a deep copy is returned.

    When ``dae_support`` is ``True`` (the default), the function
    attempts trivial-factor elimination of algebraic equations. If all
    algebraic equations are eliminated, the output is a pure-ODE
    system with ``metadata.system_class = "ode"``. If any remain, the
    call raises :class:`DiscretizationError` with code
    ``E_NONTRIVIAL_DAE``.

    When ``dae_support`` is ``False``, no factoring is attempted and
    the presence of any algebraic equation raises
    ``E_NO_DAE_SUPPORT``.

    ``dae_support=None`` (the default) consults the environment
    variable ``ESM_DAE_SUPPORT``; any of ``"0"``, ``"false"``,
    ``"off"``, ``"no"`` (case-insensitive) disables, and absence or
    any other value enables.

    Regardless of which path runs, the output carries
    ``metadata.system_class`` (``"ode"`` / ``"dae"``) and
    ``metadata.dae_info`` (``algebraic_equation_count``, ``per_model``)
    measured on the final equation set.
    """
    if not isinstance(esm, dict):
        raise TypeError(
            f"discretize: input must be a dict; got {type(esm).__name__}"
        )
    if dae_support is None:
        dae_support = _default_dae_support()

    out = copy.deepcopy(esm)
    indep_by_domain = _indep_var_by_domain(out)

    total_algebraic = 0
    per_model: Dict[str, int] = {}
    residual_paths: List[str] = []
    residual_equations: List[Dict[str, Any]] = []

    models = out.get("models")
    if isinstance(models, dict):
        for mname, mraw in models.items():
            if not isinstance(mraw, dict):
                per_model[str(mname)] = 0
                continue
            indep = _model_independent_variable(mraw, indep_by_domain)
            count, eq_residual_paths, eq_residual = _discretize_model(
                str(mname), mraw, indep, dae_support=dae_support
            )
            per_model[str(mname)] = count
            total_algebraic += count
            residual_paths.extend(eq_residual_paths)
            residual_equations.extend(eq_residual)

    meta = _ensure_dict(out, "metadata")
    meta["system_class"] = "dae" if total_algebraic > 0 else "ode"
    meta["dae_info"] = {
        "algebraic_equation_count": total_algebraic,
        "per_model": dict(per_model),
    }

    if total_algebraic > 0:
        if not dae_support:
            where = residual_paths[0] if residual_paths else "(unknown)"
            raise DiscretizationError(
                "E_NO_DAE_SUPPORT",
                f"discretize() output contains {total_algebraic} algebraic "
                f"equation(s) (first at {where}); DAE support is disabled "
                "(dae_support=False / ESM_DAE_SUPPORT=0). Enable DAE "
                "support or remove the algebraic constraint(s). See RFC §12.",
            )
        # With dae_support=True, any surviving algebraic equation is
        # non-trivial for the Python binding.
        raise DiscretizationError(
            "E_NONTRIVIAL_DAE",
            _nontrivial_dae_message(total_algebraic, residual_paths, residual_equations),
        )

    # Record provenance.
    in_meta = esm.get("metadata") if isinstance(esm.get("metadata"), dict) else None
    if in_meta is not None and "name" in in_meta:
        meta["discretized_from"] = in_meta["name"]

    return out


# ---------------------------------------------------------------------------
# Model-level factoring
# ---------------------------------------------------------------------------


def _discretize_model(
    mname: str,
    model: Dict[str, Any],
    indep: str,
    *,
    dae_support: bool,
) -> Tuple[int, List[str], List[Dict[str, Any]]]:
    """Classify, factor, and rewrite the equations of one model in place.

    Returns ``(residual_algebraic_count, residual_paths, residual_equations)``.
    The model's ``equations`` list is replaced with the factored
    differential equations plus any non-factorable algebraic
    equations (the latter only when factoring was skipped because
    ``dae_support=False``).
    """
    raw_equations = model.get("equations")
    if not isinstance(raw_equations, list):
        return 0, [], []

    # Classify equations.
    differential: List[Tuple[int, Dict[str, Any]]] = []
    algebraic: List[Tuple[int, Dict[str, Any]]] = []
    for i, eq in enumerate(raw_equations):
        if not isinstance(eq, dict):
            continue
        if _is_algebraic_equation(eq, indep):
            algebraic.append((i, eq))
        else:
            differential.append((i, eq))

    if not algebraic:
        return 0, [], []

    if not dae_support:
        # Skip factoring entirely; all algebraic equations count.
        paths = [f"models.{mname}.equations[{i}]" for i, _ in algebraic]
        residual_eqs = [eq for _, eq in algebraic]
        return len(algebraic), paths, residual_eqs

    subs, unfactorable = _build_trivial_substitutions(algebraic)

    # Apply substitutions to the differential equation RHS (and LHS for
    # completeness, though LHS is normally D(x, wrt=t) and substitution
    # is a no-op there).
    if subs:
        new_differential: List[Tuple[int, Dict[str, Any]]] = []
        for i, eq in differential:
            new_eq = dict(eq)
            if "lhs" in new_eq:
                new_eq["lhs"] = _substitute(new_eq["lhs"], subs)
            if "rhs" in new_eq:
                new_eq["rhs"] = _substitute(new_eq["rhs"], subs)
            new_differential.append((i, new_eq))
        differential = new_differential

    # Rebuild the equations list in stable original order, dropping
    # factored algebraic equations. Unfactorable algebraic equations are
    # retained in the output so that a downstream binding or a
    # future DAE solver can still see them; E_NONTRIVIAL_DAE will be
    # raised by the caller.
    eliminated_indices: Set[int] = {i for i, _ in algebraic if i not in {idx for idx, _ in unfactorable}}
    new_equations: List[Dict[str, Any]] = []
    idx_to_new_eq = {i: eq for i, eq in differential}
    idx_to_raw = {i: eq for i, eq in algebraic}
    for i, _orig in enumerate(raw_equations):
        if i in eliminated_indices:
            continue
        if i in idx_to_new_eq:
            new_equations.append(idx_to_new_eq[i])
        elif i in idx_to_raw:
            new_equations.append(idx_to_raw[i])
        else:
            new_equations.append(_orig)
    model["equations"] = new_equations

    if unfactorable:
        paths = [f"models.{mname}.equations[{i}]" for i, _ in unfactorable]
        residual_eqs = [eq for _, eq in unfactorable]
        return len(unfactorable), paths, residual_eqs
    return 0, [], []


def _build_trivial_substitutions(
    algebraic: Sequence[Tuple[int, Dict[str, Any]]],
) -> Tuple[Dict[str, Any], List[Tuple[int, Dict[str, Any]]]]:
    """Topologically order ``var = expr`` algebraic equations.

    Returns ``(substitutions, unfactorable)``.

    * ``substitutions[var]`` is the RHS of ``var = rhs`` with *all prior*
      substitutions already applied, so callers can inline the
      substitution directly into any expression without recursion.
    * ``unfactorable`` contains the ``(index, equation)`` pairs that
      could not be factored: LHS not a bare variable, self-reference
      on RHS, or a cycle among algebraic equations.
    """
    # First pass: only accept bare-string LHS. Anything else (``0 = g(x)``
    # or an indexed LHS) is immediately unfactorable.
    candidates: Dict[str, Tuple[int, Dict[str, Any], Any]] = {}  # name -> (idx, eq, rhs)
    unfactorable: List[Tuple[int, Dict[str, Any]]] = []
    name_order: List[str] = []  # preserve original equation order for stable output
    for idx, eq in algebraic:
        lhs = eq.get("lhs")
        rhs = eq.get("rhs")
        if isinstance(lhs, str) and lhs and rhs is not None and lhs not in candidates:
            candidates[lhs] = (idx, eq, rhs)
            name_order.append(lhs)
        else:
            unfactorable.append((idx, eq))

    # Topological sort: a candidate can be substituted once every
    # algebraic-LHS variable its RHS depends on has been resolved.
    subs: Dict[str, Any] = {}
    resolved: Set[str] = set()
    pending = list(name_order)
    while pending:
        progress = False
        next_round: List[str] = []
        for name in pending:
            idx, eq, rhs = candidates[name]
            deps = _free_vars(rhs) & set(candidates.keys())
            # Self-reference forbids factoring.
            if name in deps:
                unfactorable.append((idx, eq))
                continue
            unresolved_deps = deps - resolved
            if unresolved_deps:
                next_round.append(name)
                continue
            # Inline already-resolved substitutions into this RHS.
            subs[name] = _substitute(rhs, subs)
            resolved.add(name)
            progress = True
        if not progress:
            # Cycle among remaining names (or all depend on
            # already-declared-unfactorable names). Mark the rest as
            # unfactorable.
            for name in next_round:
                idx, eq, _ = candidates[name]
                unfactorable.append((idx, eq))
            break
        pending = next_round

    # Preserve discovery order so residual paths are stable.
    unfactorable.sort(key=lambda pair: pair[0])
    return subs, unfactorable


# ---------------------------------------------------------------------------
# Expression utilities (operate on raw dict/JSON form)
# ---------------------------------------------------------------------------


def _substitute(expr: Any, subs: Dict[str, Any]) -> Any:
    """Replace bare-string variable references with their substitution.

    Operates on the raw JSON form of an ESM expression (int/float/str
    or a ``dict`` with an ``op`` key). Substitution values are deep-copied
    so the output is independent of the caller's substitution map.
    """
    if not subs:
        return expr
    if isinstance(expr, str):
        if expr in subs:
            return copy.deepcopy(subs[expr])
        return expr
    if isinstance(expr, dict):
        new = {}
        for k, v in expr.items():
            if k == "args" and isinstance(v, list):
                new[k] = [_substitute(a, subs) for a in v]
            elif k == "expr":
                new[k] = _substitute(v, subs)
            elif k == "values" and isinstance(v, list):
                new[k] = [_substitute(a, subs) for a in v]
            else:
                new[k] = v
        return new
    return expr


def _free_vars(expr: Any) -> Set[str]:
    """Collect bare-string variable names referenced in an expression."""
    out: Set[str] = set()
    _collect_free_vars(expr, out)
    return out


def _collect_free_vars(expr: Any, out: Set[str]) -> None:
    if isinstance(expr, str):
        out.add(expr)
        return
    if isinstance(expr, dict):
        args = expr.get("args")
        if isinstance(args, list):
            for a in args:
                _collect_free_vars(a, out)
        body = expr.get("expr")
        if body is not None:
            _collect_free_vars(body, out)
        values = expr.get("values")
        if isinstance(values, list):
            for v in values:
                _collect_free_vars(v, out)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def _is_algebraic_equation(eq: Dict[str, Any], indep: str) -> bool:
    """Return ``True`` iff ``eq`` is algebraic per RFC §12.

    An equation is algebraic iff any of these hold:
    * ``produces`` is ``"algebraic"`` or ``{"kind": "algebraic"}``.
    * ``algebraic`` is truthy.
    * LHS is not a ``D(x, wrt=<indep>)`` operator node (catches
      observed-equation LHS and explicit ``0 = g(x)`` constraints).
    Malformed equations (missing LHS) are treated as algebraic so the
    contract fails closed.
    """
    produces = eq.get("produces")
    if produces == "algebraic":
        return True
    if isinstance(produces, dict) and produces.get("kind") == "algebraic":
        return True
    if eq.get("algebraic"):
        return True
    lhs = eq.get("lhs")
    if lhs is None:
        return True
    if isinstance(lhs, dict) and lhs.get("op") == "D":
        wrt = lhs.get("wrt")
        # wrt=None or wrt==indep is a differential equation.
        if wrt is None or wrt == indep:
            return False
        return True
    return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _indep_var_by_domain(esm: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    domains = esm.get("domains")
    if isinstance(domains, dict):
        for dname, draw in domains.items():
            if isinstance(draw, dict):
                iv = draw.get("independent_variable")
                out[str(dname)] = str(iv) if isinstance(iv, str) else "t"
    return out


def _model_independent_variable(
    model: Dict[str, Any], indep_by_domain: Dict[str, str]
) -> str:
    dname = model.get("domain")
    if isinstance(dname, str):
        return indep_by_domain.get(dname, "t")
    return "t"


def _ensure_dict(container: Dict[str, Any], key: str) -> Dict[str, Any]:
    raw = container.get(key)
    if isinstance(raw, dict):
        return raw
    new: Dict[str, Any] = {}
    container[key] = new
    return new


def _default_dae_support() -> bool:
    raw = os.environ.get("ESM_DAE_SUPPORT")
    if raw is None:
        return True
    return raw.strip().lower() not in ("0", "false", "off", "no")


def _nontrivial_dae_message(
    count: int,
    paths: Sequence[str],
    equations: Sequence[Dict[str, Any]],
) -> str:
    head = paths[0] if paths else "(unknown)"
    listing: List[str] = []
    for path, eq in zip(paths, equations):
        lhs = eq.get("lhs")
        rhs = eq.get("rhs")
        listing.append(f"  {path}: lhs={lhs!r}, rhs={rhs!r}")
    body = "\n".join(listing) if listing else "  (no residual details)"
    return (
        f"discretize() could not factor {count} algebraic equation(s) "
        f"(first at {head}). The Python binding supports only trivial "
        f"algebraic equations (LHS a bare variable name, RHS acyclic). "
        f"For full DAE support use the Julia binding "
        f"(EarthSciSerialization.jl). See RFC §12. Residual:\n{body}"
    )
