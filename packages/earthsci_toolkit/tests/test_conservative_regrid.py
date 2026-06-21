"""End-to-end conservative-regridding assembly — Python evaluator (bead
ess-my4.4.7). RFC ``semiring-faq-unified-ir`` §A.8 / §8.1 / §6.1;
``CONFORMANCE_SPEC.md`` §5.8.

Exercises the full A.8 pipeline assembled in
:mod:`earthsci_toolkit.conservative_regrid` from the existing M1/M2/M3 machinery
plus the one geometry leaf:

1. **Broad phase** — the bin-Skolem candidate overlap-pair set is integer,
   deterministic and **permutation-invariant** (§5.8.5), and **complete** (it
   never misses a true overlap, so it is a superset of the surviving set).
2. **Narrow phase** — ``A_ij`` from the ``intersect_polygon`` clip leaf + the
   ``polygon_area`` ``sum_product`` FAQ matches the analytic overlap areas, and
   sub-``atol`` slivers snap to zero (candidate ≠ surviving, §5.8.2).
3. **Invariants** — partition-of-unity ``Σ_i W_ij = 1`` is exact by
   construction; global conservation ``Σ_j A_j·F_tgt = Σ_i A_i·F_src`` holds to
   FP for tiling grids (§5.8.3) — the primary B.5 gate.
4. The numeric core (``A_j``, the apply) is evaluated through the real
   :func:`eval_expr` FAQ machinery, and the regridder output drives a well-formed
   conservation-tracer ODE through the real :func:`simulate` driver.

``planar`` is dependency-free; the ``spherical`` path (the Julia-comparable
manifold) needs the pinned optional ``spherely`` and skips when it is absent.
"""

from __future__ import annotations

import itertools
from typing import List, Sequence, Tuple

import numpy as np
import pytest

from earthsci_toolkit import geometry as geom
from earthsci_toolkit.conservative_regrid import (
    Regridder,
    build_regridder,
    candidate_overlap_pairs,
    cell_bin_keys,
    overlap_area,
)
from earthsci_toolkit.esm_types import ExprNode
from earthsci_toolkit.numpy_interpreter import EvalContext, eval_expr
from earthsci_toolkit.parse import load
from earthsci_toolkit.simulation import simulate

try:
    import spherely  # noqa: F401

    _HAVE_SPHERELY = True
except ImportError:
    _HAVE_SPHERELY = False


# --------------------------------------------------------------------------- #
# Worked grids (two rectangular partitions of one domain → exact conservation)
# --------------------------------------------------------------------------- #

def _rect(x0: float, x1: float, y0: float, y1: float) -> np.ndarray:
    """A closed axis-aligned cell polygon as a CCW lon/lat vertex ring."""
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=float)


def _rect_overlap_area(a: np.ndarray, b: np.ndarray) -> float:
    """Analytic axis-aligned-rectangle intersection area — the independent
    cross-check for the clip-derived ``A_ij`` (no clipping involved)."""
    ax0, ay0 = a[:, 0].min(), a[:, 1].min()
    ax1, ay1 = a[:, 0].max(), a[:, 1].max()
    bx0, by0 = b[:, 0].min(), b[:, 1].min()
    bx1, by1 = b[:, 0].max(), b[:, 1].max()
    w = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    h = max(0.0, min(ay1, by1) - max(ay0, by0))
    return w * h


# Example 1 — domain [0,3]×[0,2]: 3 source columns vs 4 offset target columns.
# Refined in x only; clean partial overlaps and genuinely disjoint pairs.
_SRC_1D = [_rect(0, 1, 0, 2), _rect(1, 2, 0, 2), _rect(2, 3, 0, 2)]
_TGT_1D = [_rect(0, 0.5, 0, 2), _rect(0.5, 1.5, 0, 2), _rect(1.5, 2.5, 0, 2), _rect(2.5, 3, 0, 2)]

# Example 2 — domain [0,2]×[0,2]: 2×2 unit source vs an asymmetric 2×2 target
# split at x=1.2, y=0.8. Exercises 2-D bins and partial overlap in both axes.
_SRC_2D = [_rect(0, 1, 0, 1), _rect(1, 2, 0, 1), _rect(0, 1, 1, 2), _rect(1, 2, 1, 2)]
_TGT_2D = [_rect(0, 1.2, 0, 0.8), _rect(1.2, 2, 0, 0.8), _rect(0, 1.2, 0.8, 2), _rect(1.2, 2, 0.8, 2)]


def _src_areas(polys: Sequence[np.ndarray]) -> np.ndarray:
    return np.array([abs(geom.polygon_area(p, "planar")) for p in polys])


def _dense_A_ij(src: Sequence[np.ndarray], tgt: Sequence[np.ndarray]) -> np.ndarray:
    """``A_ij`` over ALL (i, j) pairs (no broad phase) — the reference the
    bin-Skolem candidate set must reproduce without missing an overlap."""
    out = np.zeros((len(src), len(tgt)))
    for i, j in itertools.product(range(len(src)), range(len(tgt))):
        out[i, j] = overlap_area(src[i], tgt[j], "planar")
    return out


# --------------------------------------------------------------------------- #
# (1) Broad phase — deterministic, permutation-invariant, complete candidate set
# --------------------------------------------------------------------------- #

def test_candidate_set_is_integer_and_sorted() -> None:
    pairs = candidate_overlap_pairs(_SRC_1D, _TGT_1D, 1.0, 1.0)
    assert all(isinstance(i, int) and isinstance(j, int) for i, j in pairs)
    assert pairs == sorted(pairs)  # §5.5 sorted total order


def test_candidate_set_is_permutation_invariant() -> None:
    """Reordering the input cells (and remapping indices back) yields the
    identical candidate set — the §5.8.6 adversarial permuted-input property."""
    base = candidate_overlap_pairs(_SRC_1D, _TGT_1D, 1.0, 1.0)

    src_perm = [2, 0, 1]
    tgt_perm = [3, 1, 0, 2]
    src_re = [_SRC_1D[k] for k in src_perm]
    tgt_re = [_TGT_1D[k] for k in tgt_perm]
    permuted = candidate_overlap_pairs(src_re, tgt_re, 1.0, 1.0)
    # Map permuted positions back to original indices and re-sort.
    remapped = sorted((src_perm[i], tgt_perm[j]) for i, j in permuted)
    assert remapped == base


def test_broad_phase_misses_no_overlap() -> None:
    """The candidate set is a SUPERSET of the truly-overlapping pairs: every
    (i,j) with a nonzero dense overlap is a candidate (completeness)."""
    pairs = set(candidate_overlap_pairs(_SRC_1D, _TGT_1D, 1.0, 1.0))
    dense = _dense_A_ij(_SRC_1D, _TGT_1D)
    overlapping = {(i, j) for i, j in zip(*np.nonzero(dense))}
    assert overlapping <= pairs


def test_broad_phase_excludes_disjoint_pairs() -> None:
    """Distant cells that share no bin are NOT candidates — the join actually
    prunes (here 4 of the 12 src×tgt pairs are dropped)."""
    pairs = candidate_overlap_pairs(_SRC_1D, _TGT_1D, 1.0, 1.0)
    assert len(pairs) < len(_SRC_1D) * len(_TGT_1D)
    assert (0, 3) not in pairs  # src col [0,1] vs tgt col [2.5,3] — disjoint


def test_cell_bin_keys_span_bbox_and_are_float_free() -> None:
    keys = cell_bin_keys(_rect(0.2, 2.7, 0.0, 0.5), dx=1.0, dy=1.0)
    # x spans bins floor(0.2)=0 .. floor(2.7)=2 → 3 columns; y bins floor(0)=0..floor(0.5)=0
    assert set(keys) == {("bin", 0, 0), ("bin", 1, 0), ("bin", 2, 0)}
    assert all(isinstance(c, (str, int)) for key in keys for c in key)


# --------------------------------------------------------------------------- #
# (2) Narrow phase — clip + polygon_area FAQ matches analytic; sliver floor
# --------------------------------------------------------------------------- #

def test_overlap_area_matches_analytic_unit_squares() -> None:
    a = _rect(0, 2, 0, 2)
    b = _rect(1, 3, 1, 3)
    assert overlap_area(a, b, "planar") == pytest.approx(1.0, abs=1e-12)


def test_overlap_area_disjoint_is_zero() -> None:
    assert overlap_area(_rect(0, 1, 0, 1), _rect(5, 6, 5, 6), "planar") == 0.0


@pytest.mark.parametrize(
    "src,tgt", [(_SRC_1D, _TGT_1D), (_SRC_2D, _TGT_2D)],
    ids=["1d-refine", "2d-asymmetric"],
)
def test_A_ij_matches_analytic_rectangle_overlaps(src, tgt) -> None:
    rg = build_regridder(src, tgt, manifold="planar", dx=1.0, dy=1.0, atol=1e-15)
    for i, j in itertools.product(range(len(src)), range(len(tgt))):
        assert rg.A_ij[i, j] == pytest.approx(_rect_overlap_area(src[i], tgt[j]), abs=1e-12)


def test_sliver_below_atol_snaps_to_zero() -> None:
    """A candidate that clips to a sub-``atol`` sliver is dropped from the
    SURVIVING set even though it stays in the candidate set (§5.8.2 / §5.8.5):
    "present-but-tiny" and "absent" both collapse to no contribution."""
    a = _rect(0.0, 1.0, 0.0, 1.0)
    b = _rect(1.0 - 1e-4, 2.0, 0.0, 1.0)  # overlaps by a 1e-4-wide strip → area ~1e-4
    raw = overlap_area(a, b, "planar", atol=0.0)
    assert 0.0 < raw < 1e-3
    assert overlap_area(a, b, "planar", atol=1e-3) == 0.0  # sub-atol → snapped to zero
    assert overlap_area(a, b, "planar", atol=1e-9) == pytest.approx(raw)  # above floor → kept


# --------------------------------------------------------------------------- #
# (3) Invariants — partition-of-unity (exact) + global conservation (B.5 gate)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "src,tgt", [(_SRC_1D, _TGT_1D), (_SRC_2D, _TGT_2D)],
    ids=["1d-refine", "2d-asymmetric"],
)
def test_partition_of_unity_is_exact(src, tgt) -> None:
    rg = build_regridder(src, tgt, manifold="planar", dx=1.0, dy=1.0, atol=1e-15)
    assert np.abs(rg.partition_of_unity_residual()).max() < 1e-12


@pytest.mark.parametrize(
    "src,tgt,fld", [
        (_SRC_1D, _TGT_1D, [10.0, 20.0, 30.0]),
        (_SRC_2D, _TGT_2D, [1.0, 2.0, 3.0, 4.0]),
    ],
    ids=["1d-refine", "2d-asymmetric"],
)
def test_global_conservation_is_exact_for_tiling_grids(src, tgt, fld) -> None:
    """Both grids tile the same domain, so Σ_j A_ij = A_i and conservation is
    exact to FP for an arbitrary (non-constant) source field (§5.8.3)."""
    rg = build_regridder(src, tgt, manifold="planar", dx=1.0, dy=1.0, atol=1e-15)
    resid = rg.conservation_residual(fld, src_areas=_src_areas(src))
    assert abs(resid) < 1e-12


def test_constant_field_is_reproduced_exactly() -> None:
    """A constant source field remaps to the same constant everywhere it is
    covered — a direct corollary of partition-of-unity."""
    rg = build_regridder(_SRC_2D, _TGT_2D, manifold="planar", dx=1.0, dy=1.0, atol=1e-15)
    f_tgt = rg.apply([7.0, 7.0, 7.0, 7.0])
    assert np.allclose(f_tgt, 7.0, atol=1e-12)


# --------------------------------------------------------------------------- #
# (4) The numeric core really is the FAQ IR (eval_expr) + the simulate() driver
# --------------------------------------------------------------------------- #

def test_polygon_area_faq_evaluated_via_eval_expr_matches_shoelace() -> None:
    """The ``polygon_area`` reduction is an ordinary ``sum_product`` FAQ over the
    derived clip ring, evaluated through the M1 interpreter — not hidden numpy."""
    ring = _rect(0.0, 2.0, 0.0, 3.0)  # 2×3 rectangle, area 6
    closed = np.vstack([ring, ring[:1]])  # closed ring, shape [5, 2]
    ctx = EvalContext(
        state_layout={}, state_shapes={}, param_values={}, observed_values={},
        y=np.zeros(0), t=0.0,
        index_sets={"clip_ring": {"kind": "derived", "from_faq": "overlap_clip"}},
    )
    ctx.derived_rings["overlap_clip"] = closed

    def col(idx, c):
        return ExprNode(op="index", args=["overlap_clip", idx, c])

    v1 = ExprNode(op="+", args=["v", 1])
    cross = ExprNode(op="-", args=[
        ExprNode(op="*", args=[col("v", 1), col(v1, 2)]),
        ExprNode(op="*", args=[col(v1, 1), col("v", 2)]),
    ])
    faq = ExprNode(op="aggregate", semiring="sum_product", output_idx=[],
                   args=["overlap_clip"], ranges={"v": {"from": "clip_ring"}},
                   expr=ExprNode(op="*", args=[0.5, cross]))
    assert abs(float(eval_expr(faq, ctx))) == pytest.approx(6.0, abs=1e-12)


def test_A_j_is_a_group_by_sum_product_faq() -> None:
    """``A_j = Σ_i A_ij`` is the group-by-``j`` ``sum_product`` FAQ; the same
    AST the assembly evaluates internally reproduces the row-sums."""
    a_ij = np.array([[1.0, 1.0, 0.0, 0.0], [0.0, 1.0, 1.0, 0.0], [0.0, 0.0, 1.0, 1.0]])
    n_src, n_tgt = a_ij.shape
    ctx = EvalContext(
        state_layout={"A_ij": slice(0, a_ij.size)}, state_shapes={"A_ij": a_ij.shape},
        param_values={}, observed_values={}, y=a_ij.ravel().copy(), t=0.0,
        index_sets={"src_cells": {"kind": "interval", "size": n_src},
                    "tgt_cells": {"kind": "interval", "size": n_tgt}},
    )
    node = ExprNode(op="aggregate", semiring="sum_product", output_idx=["j"],
                    args=["A_ij"], ranges={"i": {"from": "src_cells"}, "j": {"from": "tgt_cells"}},
                    expr=ExprNode(op="index", args=["A_ij", "i", "j"]))
    assert np.allclose(np.asarray(eval_expr(node, ctx)), a_ij.sum(axis=0))


def test_conservation_tracer_runs_through_simulate_driver() -> None:
    """The regridder output feeds a well-formed conservation-tracer ODE — the
    fixture's ``mass_tgt`` equation — through the real ``simulate`` driver:
    ``d(mass)/dt = Σ_j A_j·F_tgt[j]`` integrates to the conserved global mass."""
    src, tgt, f_src = _SRC_1D, _TGT_1D, [10.0, 20.0, 30.0]
    rg = build_regridder(src, tgt, manifold="planar", dx=1.0, dy=1.0, atol=1e-15)
    f_tgt = rg.apply(f_src)
    integrand = rg.A_j * f_tgt  # the per-target-cell mass-rate factor
    n = len(integrand)

    model = {
        "esm": "0.6.0",
        "metadata": {"name": "regrid_conservation_tracer"},
        "models": {"Tracer": {
            "index_sets": {"tgt": {"kind": "interval", "size": n}},
            "variables": {
                "rate": {"type": "state", "shape": ["j"]},
                "mass": {"type": "state"},
            },
            "equations": [
                {  # d(rate[j])/dt = 0 — hold the precomputed integrand constant
                    "lhs": {"op": "aggregate", "args": [], "output_idx": ["j"],
                            "expr": {"op": "D", "args": [{"op": "index", "args": ["rate", "j"]}], "wrt": "t"},
                            "ranges": {"j": [1, n]}},
                    "rhs": {"op": "aggregate", "args": [], "output_idx": ["j"],
                            "semiring": "sum_product", "expr": 0.0, "ranges": {"j": [1, n]}},
                },
                {  # d(mass)/dt = Σ_j rate[j] — the conservation tracer (sum_product FAQ)
                    "lhs": {"op": "D", "args": ["mass"], "wrt": "t"},
                    "rhs": {"op": "aggregate", "args": [], "output_idx": [],
                            "semiring": "sum_product", "expr": {"op": "index", "args": ["rate", "j"]},
                            "ranges": {"j": {"from": "tgt"}}},
                },
            ],
        }},
    }
    ics = {f"rate[{k + 1}]": float(integrand[k]) for k in range(n)}
    ics["mass"] = 0.0
    res = simulate(load(model), (0.0, 1.0), initial_conditions=ics)
    assert res.success, res.message

    mass_idx = next(i for i, v in enumerate(res.vars) if v.split(".")[-1] == "mass")
    mass_final = float(np.asarray(res.y)[mass_idx, -1])
    # Σ_j A_j·F_tgt·(t=1) == the conserved source mass Σ_i A_i·F_src.
    expected = float(_src_areas(src) @ np.asarray(f_src))
    assert mass_final == pytest.approx(expected, rel=1e-6)


# --------------------------------------------------------------------------- #
# (5) The shared structural fixture is consistent with this assembly
# --------------------------------------------------------------------------- #

def test_overlap_join_fixture_describes_this_assembly() -> None:
    """The shared worked fixture (bead ess-my4.4.5) declares exactly the index
    sets / state variables this assembly realizes — a guard that the structural
    fixture and the executable assembly stay in lock-step."""
    from pathlib import Path

    repo = Path(__file__).resolve().parents[3]
    fixture = repo / "tests" / "valid" / "geometry" / "conservative_regrid_overlap_join.esm"
    model = load(str(fixture)).models["ConservativeRegridOverlapJoin"]
    # The A.8 chain variables are all present. The fixture is now the SINGLE
    # end-to-end-evaluable document (bead ess-3lj.3): A_j / F_tgt are the
    # arrayop-D-from-zero-IC assembly states gated on the materialised bin buffers,
    # dst_areas is the build-once denominator, and narrow_phase_area consumes the
    # spherical clip + Van Oosterom-Strackee polygon_area FAQ.
    for name in ("A_ij", "A_j", "F_src", "F_tgt", "src_bin", "tgt_bin", "pair_exists",
                 "dst_areas", "narrow_phase_area"):
        assert name in model.variables
    # The candidate set is a derived index set produced by the bin-Skolem join.
    assert model.index_sets["candidate_pairs"]["kind"] == "derived"


# --------------------------------------------------------------------------- #
# (6) Spherical — the Julia-comparable manifold (needs spherely / S2)
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(not _HAVE_SPHERELY, reason="spherely (S2) not installed")
def test_spherical_assembly_invariants_hold() -> None:
    """Under the ``spherical`` manifold the same invariants hold: partition-of-
    unity exact by construction, conservation exact for tiling lon/lat grids
    (great-circle edges; the B.5 cross-binding gate is ess-my4.4.8)."""
    # Small near-equatorial lon/lat cells (degrees) so spherical ≈ planar in rad².
    src = [_rect(0, 1, 0, 2), _rect(1, 2, 0, 2), _rect(2, 3, 0, 2)]
    tgt = [_rect(0, 0.5, 0, 2), _rect(0.5, 1.5, 0, 2), _rect(1.5, 2.5, 0, 2), _rect(2.5, 3, 0, 2)]
    rg = build_regridder(src, tgt, manifold="spherical", dx=1.0, dy=1.0,
                         atol=geom.SLIVER_ATOL_FACTOR)
    assert np.abs(rg.partition_of_unity_residual()).max() < 1e-9
    src_areas = np.array([abs(geom.polygon_area(p, "spherical")) for p in src])
    resid = rg.conservation_residual([10.0, 20.0, 30.0], src_areas=src_areas)
    assert abs(resid) < 1e-9
