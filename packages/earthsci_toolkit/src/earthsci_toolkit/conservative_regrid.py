"""First-order conservative-regridding assembly (RFC ``semiring-faq-unified-ir``
§A.8 / §8.1 / §6.1; ``CONFORMANCE_SPEC.md`` §5.8; bead ess-my4.4.7).

This is the **Python per-binding assembly** of the conservative regridder — the
``F_tgt[j] = (1/A_j)·Σ_i A_ij·F_src[i]`` operator, with
``A_ij = area(src_i ∩ tgt_j)`` and ``A_j = Σ_i A_ij`` — composed entirely from
the already-landed M1/M2/M3 machinery plus the one geometry leaf, exactly as the
A.8 decomposition prescribes. Nothing here is a new physical operator:

==========================  ===========================================  ============
A.8 piece                   realized by                                  partition
==========================  ===========================================  ============
overlap pairs {(i,j)}       bin-Skolem equi-join — the build-time         static
                            relational engine (:mod:`.relational`:
                            ``skolem`` bins + ``equijoin`` + ``distinct``)
A_ij                        the ``intersect_polygon`` clip leaf           static
                            (:mod:`.geometry`) + the ``polygon_area``
                            ``sum_product`` FAQ (:func:`.eval_expr`)
A_j = Σ_i A_ij              group-by-``j`` ``sum_product`` FAQ            static
apply Σ_i A_ij·F_src[i]     ``sum_product`` FAQ (sparse mat-vec)          dynamic
/A_j                        elementwise (foldable to build time)          static fold
==========================  ===========================================  ============

The broad phase (which pairs are *candidates*) is **integer-keyed and
byte-identical** across bindings (§5.8.5): every cell is quantized to the integer
spatial bins its bounding box spans (``floor`` + ``skolem``), and the candidates
are the equi-join of cells sharing a bin. No floating-point coordinate comparison
enters the broad phase — coordinates touch only the narrow-phase *area*. The
narrow phase clips each candidate and keeps only sub-``atol``-surviving overlaps
(§5.8.2: "present-but-tiny" and "absent" both collapse to zero), turning the
byte-identical *candidate* set into the tolerance-dependent *surviving* set.

Partition-of-unity ``Σ_i W_ij = 1`` holds **by construction** because the
denominator ``A_j`` is the row-sum of the *same* computed overlap areas
(``ConservativeRegridding.jl``'s ``dst_areas``), so it is exact regardless of
edge-model error (§5.8.3). Global conservation
``Σ_j A_j·F_tgt[j] = Σ_i A_i·F_src[i]`` holds exactly when the target grid tiles
the source domain (``Σ_j A_ij = A_i``); otherwise it is tolerance-/resolution-set.

This module does **not** modify the ``simulate()`` ODE driver or the interpreter:
it composes their *public* evaluation surfaces. Wiring the derived clip-ring
observed straight into the ODE driver is the separate concern of bead
ess-my4.4.13; the M4 cross-binding conformance gate is ess-my4.4.8.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import numpy as np

from . import geometry
from .esm_types import ExprNode
from .numpy_interpreter import EvalContext, eval_expr
from .relational import distinct, equijoin, skolem

__all__ = [
    "Regridder",
    "build_regridder",
    "candidate_overlap_pairs",
    "cell_bin_keys",
    "overlap_area",
    "DEFAULT_RTOL",
]

# Polygon = closed-or-open lon/lat vertex ring, shape [n, 2].
Polygon = np.ndarray
# A Skolem bin key — the content-addressed ("bin", bx, by) tuple (§5.8.5).
BinKey = Tuple[object, ...]

#: Tag prefix the broad-phase bin Skolem keys carry, mirroring the worked
#: fixture ``tests/valid/geometry/conservative_regrid_overlap_join.esm``.
BIN_TAG = "bin"

#: Default per-pair area relative tolerance for the §5.8.2 / B.5 gate. The
#: absolute sliver floor is ``geometry.SLIVER_ATOL_FACTOR · R²``.
DEFAULT_RTOL = 1e-9


# --------------------------------------------------------------------------- #
# (1) OVERLAP PAIRS — the bin-Skolem equi-join broad phase (M3, build-time)
# --------------------------------------------------------------------------- #

def cell_bin_keys(poly: Polygon, dx: float, dy: float) -> List[BinKey]:
    """Every integer spatial-bin Skolem key the cell's bounding box spans.

    The cell is quantized to the integer lattice ``floor(coord/step)`` (the
    existing ``floor`` op — no bespoke binning leaf) and a key is minted with
    :func:`.skolem` for **each** bin its bbox touches. Binning by the full bbox
    span (not a single representative corner) is what makes the broad phase
    *complete* — it can never miss a true overlap, so the candidate set is a
    genuine superset of the surviving-overlap set (§5.8.5).

    Keys are integer-componented tuples, so the resulting candidate set is
    byte-identical across bindings (§5.5 determinism — no float in a key).
    """
    ring = np.asarray(poly, dtype=float)
    lon, lat = ring[:, 0], ring[:, 1]
    bx_lo = int(np.floor(lon.min() / dx))
    bx_hi = int(np.floor(lon.max() / dx))
    by_lo = int(np.floor(lat.min() / dy))
    by_hi = int(np.floor(lat.max() / dy))
    return [
        skolem((BIN_TAG, bx, by))
        for bx in range(bx_lo, bx_hi + 1)
        for by in range(by_lo, by_hi + 1)
    ]


def candidate_overlap_pairs(
    src_polys: Sequence[Polygon],
    tgt_polys: Sequence[Polygon],
    dx: float,
    dy: float,
) -> List[Tuple[int, int]]:
    """The bin-Skolem candidate overlap-pair set ``{(i, j)}`` (broad phase).

    Realized as a value-equality :func:`.equijoin` of the ``(bin_key, cell)``
    tables of source and target on the shared bin key, then :func:`.distinct`
    over the surviving ``(i, j)`` index pairs. Both primitives emit in the §5.5
    sorted total order, so the returned list is the **byte-identical, integer,
    permutation-invariant** candidate set the §5.8.6 gate asserts on — neither
    the order of ``src_polys``/``tgt_polys`` nor bucket iteration order can
    perturb it.
    """
    src_rows = [(key, i) for i, p in enumerate(src_polys) for key in cell_bin_keys(p, dx, dy)]
    tgt_rows = [(key, j) for j, p in enumerate(tgt_polys) for key in cell_bin_keys(p, dx, dy)]
    matched = equijoin(
        src_rows, tgt_rows, on_left=lambda r: r[0], on_right=lambda r: r[0]
    )
    pairs = [(left[1], right[1]) for left, right in matched]
    return [tuple(p) for p in distinct(pairs)]


# --------------------------------------------------------------------------- #
# (2) A_ij — the intersect_polygon clip leaf + the polygon_area FAQ (M4 + M1)
# --------------------------------------------------------------------------- #

def _clip_ctx(poly_a: Polygon, poly_b: Polygon) -> EvalContext:
    """An :class:`EvalContext` exposing the two operand rings as ``poly_a`` /
    ``poly_b`` and declaring the derived clip-ring index set ``clip_ring``."""
    a = np.asarray(poly_a, dtype=float)
    b = np.asarray(poly_b, dtype=float)
    return EvalContext(
        state_layout={"poly_a": slice(0, a.size), "poly_b": slice(a.size, a.size + b.size)},
        state_shapes={"poly_a": a.shape, "poly_b": b.shape},
        param_values={},
        observed_values={},
        y=np.concatenate([a.ravel(), b.ravel()]),
        t=0.0,
        index_sets={"clip_ring": {"kind": "derived", "from_faq": "overlap_clip"}},
    )


def _shoelace_area_faq() -> ExprNode:
    """The planar ``polygon_area`` FAQ over the derived clip ring:
    ``0.5·Σ_v (x_v·y_{v+1} − x_{v+1}·y_v)`` — an ordinary ``sum_product``
    aggregate (§8.1), the same AST baked into the planar geometry fixture."""
    def col(idx: object, c: int) -> ExprNode:
        return ExprNode(op="index", args=["overlap_clip", idx, c])

    v_next = ExprNode(op="+", args=["v", 1])
    cross = ExprNode(op="-", args=[
        ExprNode(op="*", args=[col("v", 1), col(v_next, 2)]),
        ExprNode(op="*", args=[col(v_next, 1), col("v", 2)]),
    ])
    return ExprNode(
        op="aggregate", semiring="sum_product", output_idx=[], args=["overlap_clip"],
        ranges={"v": {"from": "clip_ring"}}, expr=ExprNode(op="*", args=[0.5, cross]),
    )


# Degrees→radians factor — the same constant ``math.radians`` applies, so the
# FAQ's lon-lat→sphere map matches the imperative oracle to the last ULP.
_DEG2RAD = math.pi / 180.0


def _clip_unit_vec(idx: object) -> Tuple[ExprNode, ExprNode, ExprNode]:
    """AST for the unit 3-vector of clip-ring vertex ``idx`` (lon = col 1, lat =
    col 2, degrees): ``(cosφ·cosλ, cosφ·sinλ, sinφ)`` — the same lon-lat→sphere map
    the oracle :func:`geometry._lonlat_to_unit` uses, built from the ``sin`` / ``cos``
    scalar leaves so the per-triangle excess is a closed-form AST (no new op)."""
    def col(c: int) -> ExprNode:
        return ExprNode(op="index", args=["overlap_clip", idx, c])

    lon = ExprNode(op="*", args=[col(1), _DEG2RAD])
    lat = ExprNode(op="*", args=[col(2), _DEG2RAD])
    cos_lat = ExprNode(op="cos", args=[lat])
    return (
        ExprNode(op="*", args=[cos_lat, ExprNode(op="cos", args=[lon])]),
        ExprNode(op="*", args=[cos_lat, ExprNode(op="sin", args=[lon])]),
        ExprNode(op="sin", args=[lat]),
    )


def _dot3(u: Tuple[ExprNode, ...], v: Tuple[ExprNode, ...]) -> ExprNode:
    """AST for the 3-vector dot product ``u·v``."""
    return ExprNode(op="+", args=[
        ExprNode(op="*", args=[u[0], v[0]]),
        ExprNode(op="*", args=[u[1], v[1]]),
        ExprNode(op="*", args=[u[2], v[2]]),
    ])


def _cross3(u: Tuple[ExprNode, ...], v: Tuple[ExprNode, ...]) -> Tuple[ExprNode, ExprNode, ExprNode]:
    """AST for the 3-vector cross product ``u×v``."""
    return (
        ExprNode(op="-", args=[ExprNode(op="*", args=[u[1], v[2]]), ExprNode(op="*", args=[u[2], v[1]])]),
        ExprNode(op="-", args=[ExprNode(op="*", args=[u[2], v[0]]), ExprNode(op="*", args=[u[0], v[2]])]),
        ExprNode(op="-", args=[ExprNode(op="*", args=[u[0], v[1]]), ExprNode(op="*", args=[u[1], v[0]])]),
    )


def _spherical_excess(
    a: Tuple[ExprNode, ...], b: Tuple[ExprNode, ...], c: Tuple[ExprNode, ...]
) -> ExprNode:
    """AST for the Van Oosterom–Strackee signed solid angle of triangle ``a,b,c``:
    ``2·atan2(a·(b×c), 1 + a·b + b·c + c·a)`` (the per-triangle term of the
    spherical-excess fan). Exact for great-circle edges, matching the spherical
    clip's geodesic-edge model (§5.8.4)."""
    triple = _dot3(a, _cross3(b, c))
    denom = ExprNode(op="+", args=[1.0, _dot3(a, b), _dot3(b, c), _dot3(c, a)])
    return ExprNode(op="*", args=[2.0, ExprNode(op="atan2", args=[triple, denom])])


def _spherical_area_faq() -> ExprNode:
    """The spherical ``polygon_area`` FAQ over the derived clip ring: the
    great-circle fan triangulation ``Σ_v E(v_1, v_v, v_{v+1})`` of Van
    Oosterom–Strackee spherical excesses — an ordinary ``sum_product`` aggregate
    (§8.1), the spherical sibling of :func:`_shoelace_area_faq`.

    Ranging the *full* closed clip ring is exact: the two degenerate fan endpoints
    contribute zero excess — ``v=1`` gives ``E(v_1, v_1, v_2)`` and ``v=n`` gives
    ``E(v_1, v_n, v_{n+1}=v_1)``, both with a collinear-with-apex vertex — so the
    sum collapses to the ``Σ_{i=2}^{n-1}`` fan the oracle
    (:func:`geometry._spherical_signed_area`) computes. This is the same trick the
    planar shoelace uses (the wrap edge ``v=n`` reads the closing vertex). Unit
    sphere (radius 1), matching the ``polygon_area`` default."""
    v_next = ExprNode(op="+", args=["v", 1])
    return ExprNode(
        op="aggregate", semiring="sum_product", output_idx=[], args=["overlap_clip"],
        ranges={"v": {"from": "clip_ring"}},
        expr=_spherical_excess(
            _clip_unit_vec(1), _clip_unit_vec("v"), _clip_unit_vec(v_next),
        ),
    )


def overlap_area(
    poly_a: Polygon,
    poly_b: Polygon,
    manifold: str,
    *,
    atol: float = 0.0,
) -> float:
    """The single-pair overlap area ``A_ij = polygon_area(src ∩ tgt)``.

    The clip is the ``intersect_polygon`` kernel leaf (evaluated through
    :func:`.eval_expr`, which registers the derived ring); the area is the
    ``polygon_area`` ``sum_product`` FAQ evaluated through the *same* interpreter —
    the planar shoelace (:func:`_shoelace_area_faq`) for ``planar`` and the
    Van Oosterom–Strackee spherical-excess fan (:func:`_spherical_area_faq`) for
    ``spherical`` / ``geodesic`` (§8.1's "shoelace / Gauss–Green / spherical
    excess"). Both are ordinary FAQs over the derived clip ring — the imperative
    :func:`geometry.polygon_area` is now only the cross-check oracle. Sub-``atol``
    slivers snap to exactly zero (§5.8.2).
    """
    ctx = _clip_ctx(poly_a, poly_b)
    clip_node = ExprNode(
        op="intersect_polygon", id="overlap_clip", manifold=manifold,
        args=["poly_a", "poly_b"],
    )
    closed = eval_expr(clip_node, ctx)  # materializes ctx.derived_rings["overlap_clip"]
    # The closed ring has n+1 rows for n distinct vertices; < 3 distinct vertices
    # (an empty or degenerate-sliver clip) is no overlap — the FAQ's degenerate
    # fan would otherwise sum FP-noise instead of an exact zero.
    if np.asarray(closed).shape[0] - 1 < 3:
        return 0.0

    faq = _shoelace_area_faq() if manifold == "planar" else _spherical_area_faq()
    area = abs(float(eval_expr(faq, ctx)))

    return 0.0 if area <= atol else area


# --------------------------------------------------------------------------- #
# (3)+(4)+(5) A_j / apply / normalize — sum_product FAQs (M1) + the regridder
# --------------------------------------------------------------------------- #

def _faq_ctx(values: Dict[str, np.ndarray], n_src: int, n_tgt: int) -> EvalContext:
    """An :class:`EvalContext` over the dense ``A_ij`` / field factors, with the
    ``src_cells`` / ``tgt_cells`` interval index sets the contraction ranges over."""
    layout: Dict[str, slice] = {}
    shapes: Dict[str, Tuple[int, ...]] = {}
    pieces: List[np.ndarray] = []
    offset = 0
    for name, arr in values.items():
        flat = np.asarray(arr, dtype=float).ravel()
        layout[name] = slice(offset, offset + flat.size)
        shapes[name] = np.asarray(arr).shape
        pieces.append(flat)
        offset += flat.size
    return EvalContext(
        state_layout=layout, state_shapes=shapes, param_values={}, observed_values={},
        y=np.concatenate(pieces) if pieces else np.zeros(0), t=0.0,
        index_sets={
            "src_cells": {"kind": "interval", "size": n_src},
            "tgt_cells": {"kind": "interval", "size": n_tgt},
        },
    )


def _sum_product_over_i(body: ExprNode) -> ExprNode:
    """``Σ_i body`` keeping ``j`` — a group-by-``j`` ``sum_product`` FAQ over the
    full ``src_cells × tgt_cells`` grid (off-candidate / sub-``atol`` entries are
    already 0 in ``A_ij``, so the dense contraction equals the sparse one)."""
    return ExprNode(
        op="aggregate", semiring="sum_product", output_idx=["j"], args=["A_ij"],
        ranges={"i": {"from": "src_cells"}, "j": {"from": "tgt_cells"}}, expr=body,
    )


@dataclass
class Regridder:
    """A built-once conservative regridder (the ``ConservativeRegridding.jl``
    ``Regridder``): the raw overlap-area matrix ``A_ij``, its row-sums ``A_j``,
    and the normalized weights ``W_ij = A_ij / A_j``."""

    candidate_pairs: List[Tuple[int, int]]
    A_ij: np.ndarray  # [n_src, n_tgt] raw overlap areas (0 off the surviving set)
    A_j: np.ndarray  # [n_tgt] = Σ_i A_ij  (dst_areas)
    weights: np.ndarray  # [n_src, n_tgt] W_ij = A_ij / A_j
    manifold: str

    @property
    def n_src(self) -> int:
        return self.A_ij.shape[0]

    @property
    def n_tgt(self) -> int:
        return self.A_ij.shape[1]

    def apply(self, f_src: Sequence[float]) -> np.ndarray:
        """Remap ``F_src`` to the target grid:
        ``F_tgt[j] = (1/A_j)·Σ_i A_ij·F_src[i]`` — the apply ``sum_product`` FAQ
        (sparse mat-vec) followed by the elementwise normalize. Evaluated through
        :func:`.eval_expr`, reusing the M1 aggregate machinery."""
        f = np.asarray(f_src, dtype=float)
        if f.shape != (self.n_src,):
            raise ValueError(f"F_src has shape {f.shape}, expected ({self.n_src},)")
        ctx = _faq_ctx({"A_ij": self.A_ij, "F_src": f}, self.n_src, self.n_tgt)
        numerator = np.asarray(eval_expr(
            _sum_product_over_i(ExprNode(op="*", args=[
                ExprNode(op="index", args=["A_ij", "i", "j"]),
                ExprNode(op="index", args=["F_src", "i"]),
            ])),
            ctx,
        ), dtype=float)
        out = np.zeros(self.n_tgt, dtype=float)
        nz = self.A_j > 0.0
        out[nz] = numerator[nz] / self.A_j[nz]
        return out

    def partition_of_unity_residual(self) -> np.ndarray:
        """``Σ_i W_ij − 1`` per target cell — zero (to FP) by construction for
        every cell with a nonzero overlap (§5.8.3)."""
        covered = self.A_j > 0.0
        res = np.zeros(self.n_tgt, dtype=float)
        res[covered] = self.weights[:, covered].sum(axis=0) - 1.0
        return res

    def conservation_residual(
        self, f_src: Sequence[float], src_areas: Sequence[float]
    ) -> float:
        """``Σ_j A_j·F_tgt[j] − Σ_i A_i·F_src[i]`` — the global-mass residual
        (§5.8.3). Zero (to FP) when the target grid tiles the source domain."""
        f = np.asarray(f_src, dtype=float)
        a_i = np.asarray(src_areas, dtype=float)
        f_tgt = self.apply(f)
        return float(self.A_j @ f_tgt - a_i @ f)


def build_regridder(
    src_polys: Sequence[Polygon],
    tgt_polys: Sequence[Polygon],
    *,
    manifold: str = "planar",
    dx: float,
    dy: float,
    atol: float = 0.0,
) -> Regridder:
    """Build the conservative regridder for a source/target cell-polygon pair.

    Runs the full A.8 static partition: broad-phase bin-Skolem candidate join
    (:func:`candidate_overlap_pairs`), narrow-phase clip + ``polygon_area`` FAQ
    for each candidate (:func:`overlap_area`, sub-``atol`` slivers dropped), the
    group-by-``j`` row-sum ``A_j`` (a ``sum_product`` FAQ via :func:`.eval_expr`),
    and the normalize ``W_ij = A_ij / A_j``.
    """
    if manifold not in geometry.MANIFOLDS:
        raise ValueError(f"unknown manifold {manifold!r}; expected one of {geometry.MANIFOLDS}")
    n_src, n_tgt = len(src_polys), len(tgt_polys)
    pairs = candidate_overlap_pairs(src_polys, tgt_polys, dx, dy)

    a_ij = np.zeros((n_src, n_tgt), dtype=float)
    for i, j in pairs:
        a_ij[i, j] = overlap_area(src_polys[i], tgt_polys[j], manifold, atol=atol)

    ctx = _faq_ctx({"A_ij": a_ij}, n_src, n_tgt)
    a_j = np.asarray(eval_expr(
        _sum_product_over_i(ExprNode(op="index", args=["A_ij", "i", "j"])), ctx,
    ), dtype=float)

    weights = np.zeros_like(a_ij)
    covered = a_j > 0.0
    weights[:, covered] = a_ij[:, covered] / a_j[covered]
    return Regridder(
        candidate_pairs=pairs, A_ij=a_ij, A_j=a_j, weights=weights, manifold=manifold,
    )
