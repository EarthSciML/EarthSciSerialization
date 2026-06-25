"""Cross-binding parity for declarative BC lowering in :mod:`spatial_discretize`.

These tests pin the Python BC lowering to the **Julia reference**
(``EarthSciSerialization.jl/test/discretize_test.jl`` testset "non-periodic BCs:
makearray-region ghost lowering (ess-hjg)" and
``tests/conformance/discretize/golden/interface_bc_lowering.json``). The BC ghost
is produced by the **shared rule engine** applied to a synthetic ``bc`` op — the
same ESD ``{dirichlet,neumann,robin}_bc.json`` rules Julia consumes — never by a
per-kind Python table. Every kind (dirichlet / neumann / zero_gradient / robin /
interface) and 2-D corners flow through the one generic makearray path.

The numeric anchors (``u[k] = k`` -> exact RHS) are byte-for-byte the Julia
testset's anchors, so a divergence in either binding surfaces as a failure here.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from earthsci_toolkit.numpy_interpreter import eval_expr, EvalContext
from earthsci_toolkit.rule_engine import _parse_expr
from earthsci_toolkit.spatial_discretize import spatial_discretize, _discretize_bc, \
    _bc_rules, _bc_rule_ctx


# --- the ESD ghost rules, inlined exactly as the Julia reference test does -----
# (mirror ESD finite_difference/{dirichlet,neumann,robin}_bc.json; local 0-based
# index($u,0) = first interior cell; $h from bind_side_spacing = 1/N). Robin
# coefficients ride as trailing pattern args $a,$b,$g.
_DIRICHLET = {"name": "dirichlet_bc",
    "pattern": {"op": "bc", "kind": "dirichlet", "side": "$side", "args": ["$u", "$value"]},
    "replacement": {"op": "-", "args": [{"op": "*", "args": [2, "$value"]},
                                        {"op": "index", "args": ["$u", 0]}]}}
_NEUMANN = {"name": "neumann_bc",
    "pattern": {"op": "bc", "kind": "neumann", "side": "$side", "args": ["$u", "$value"]},
    "where": [{"guard": "var_has_grid", "pvar": "$u", "grid": "$g"},
              {"guard": "bind_side_spacing", "pvar": "$h", "side": "$side", "grid": "$g"}],
    "replacement": {"op": "+", "args": [{"op": "index", "args": ["$u", 0]},
                                        {"op": "*", "args": ["$h", "$value"]}]}}
_ROBIN = {"name": "robin_bc",
    "pattern": {"op": "bc", "kind": "robin", "side": "$side", "args": ["$u", "$a", "$b", "$g"]},
    "where": [{"guard": "var_has_grid", "pvar": "$u", "grid": "$gr"},
              {"guard": "bind_side_spacing", "pvar": "$h", "side": "$side", "grid": "$gr"}],
    "replacement": {"op": "/", "args": [
        {"op": "+", "args": [
            {"op": "*", "args": [{"op": "*", "args": [2, "$h"]}, "$g"]},
            {"op": "*", "args": [
                {"op": "-", "args": [{"op": "*", "args": [2, "$b"]}, {"op": "*", "args": ["$a", "$h"]}]},
                {"op": "index", "args": ["$u", 0]}]}]},
        {"op": "+", "args": [{"op": "*", "args": ["$a", "$h"]}, {"op": "*", "args": [2, "$b"]}]}]}}

# grad(u) -> -u[x-1] + u[x+1] (un-normalized, matching the Julia anchors).
_GRAD = {"discretizations": {"grad": {"discretizations": {"g": {
    "applies_to": {"op": "grad", "args": ["$u"], "dim": "$x"}, "grid_family": "cartesian",
    "replacement": {"op": "arrayop", "output_idx": ["$x"], "args": ["$u"], "expr": {"op": "+", "args": [
        {"op": "*", "args": [-1, {"op": "index", "args": ["$u", {"op": "+", "args": ["$x", -1]}]}]},
        {"op": "index", "args": ["$u", {"op": "+", "args": ["$x", 1]}]}]}}}}}}}


def _bounded_1d_esm(right, rules=(_DIRICHLET, _NEUMANN, _ROBIN)):
    """8-cell bounded heat-like model: D(u) = grad(u), Dirichlet u(xmin)=3 plus a
    configurable right BC (mirror Julia ``_bounded_1d_esm``)."""
    return {"esm": "0.5.0", "metadata": {"name": "B"}, "rules": list(rules),
        "domains": {"line": {"independent_variable": "t",
            "spatial": {"x": {"min": 0.0, "max": 1.0, "grid_spacing": 1.0 / 7}}}},  # 8 points
        "models": {"M": {"domain": "line", "system_kind": "pde",
            "variables": {"u": {"type": "state", "units": "1"}},
            "boundary_conditions": {
                "left": {"variable": "u", "kind": "dirichlet", "side": "xmin", "value": 3},
                "right": right},
            "equations": [{"lhs": {"op": "D", "args": ["u"], "wrt": "t"},
                           "rhs": {"op": "grad", "args": ["u"], "dim": "x"}}]}}}


def _eval_rhs(disc, model, state, vec):
    """Evaluate the discretized arrayop RHS at a concrete 1-D state (the Python
    analog of Julia ``build_evaluator``)."""
    rhs = disc["models"][model]["equations"][0]["rhs"]
    y = np.asarray(vec, dtype=float)
    ctx = EvalContext(state_layout={state: slice(0, y.size)}, state_shapes={state: (y.size,)},
                      param_values={}, observed_values={}, y=y, t=0.0)
    return np.asarray(eval_expr(_parse_expr(rhs), ctx), dtype=float)


def _ma(disc, model="M"):
    return disc["models"][model]["equations"][0]["rhs"]["expr"]["args"][0]


def test_makearray_regions_match_julia():
    """ONE arrayop over the full grid; the boundary ghosts ride in a makearray
    body with the interior box + the two boundary single cells, exactly as the
    Julia reference (regions [[1,8]],[[1,1]],[[8,8]] there; the interior box is
    [2,7] here — numerically identical, boundary cells override it)."""
    disc = spatial_discretize(
        _bounded_1d_esm({"variable": "u", "kind": "neumann", "side": "xmax", "value": 0}), _GRAD)
    eqs = disc["models"]["M"]["equations"]
    assert len(eqs) == 1
    assert eqs[0]["lhs"]["ranges"] == {"x": [1, 8]}
    ma = _ma(disc)
    assert ma["op"] == "makearray"
    assert ma["regions"] == [[[2, 7]], [[1, 1]], [[8, 8]]]
    # No periodic folding on a bounded dim.
    assert "ifelse" not in json.dumps(eqs[0]["rhs"])
    # xmin cell: dirichlet ghost u[0] -> 2*value - u[1]; reflected u[1], no out-of-range.
    s_xmin = json.dumps(ma["values"][1])
    assert '["u", 0]' not in s_xmin
    assert '["u", 1]' in s_xmin and '["u", 2]' in s_xmin
    # xmax cell: zero-flux neumann ghost u[9] -> u[8].
    s_xmax = json.dumps(ma["values"][2])
    assert '["u", 8]' in s_xmax and '["u", 7]' in s_xmax
    assert '["u", 9]' not in s_xmax


def test_numeric_anchors_match_julia():
    """u[k]=k: interior -u[i-1]+u[i+1]=2; dirichlet i=1 -> -(2*3-u[1])+u[2]=-3;
    zero-neumann i=8 -> -u[7]+u[8]=1 (byte-identical to the Julia anchors)."""
    disc = spatial_discretize(
        _bounded_1d_esm({"variable": "u", "kind": "neumann", "side": "xmax", "value": 0}), _GRAD)
    du = _eval_rhs(disc, "M", "u", range(1, 9))
    assert du[0] == -3.0
    assert list(du[1:7]) == [2.0] * 6
    assert du[7] == 1.0


def test_nonzero_neumann_flows_through():
    """Nonzero Neumann (value=2), h=1/8 -> ghost u[8] + h*2; i=8: -u[7]+u[8]+0.25=1.25."""
    disc = spatial_discretize(
        _bounded_1d_esm({"variable": "u", "kind": "neumann", "side": "xmax", "value": 2}), _GRAD)
    du = _eval_rhs(disc, "M", "u", range(1, 9))
    assert du[7] == pytest.approx(1.25, rel=1e-12, abs=1e-12)


def test_robin_flows_through():
    """Robin a=1,b=1,g=0, h=1/8 -> ghost (2-h)*u[8]/(h+2); i=8: -u[7] + that."""
    disc = spatial_discretize(_bounded_1d_esm(
        {"variable": "u", "kind": "robin", "side": "xmax",
         "robin_alpha": 1, "robin_beta": 1, "robin_gamma": 0}), _GRAD)
    du = _eval_rhs(disc, "M", "u", range(1, 9))
    h = 1.0 / 8
    assert du[7] == pytest.approx(-7 + (2 - h) * 8 / (h + 2), rel=1e-12, abs=1e-12)


def test_bundled_defaults_used_without_document_rules():
    """No `rules` in the document -> the bundled canonical ESD ghosts still drive
    the lowering (the Dirichlet reflected ghost), so a bare model discretizes."""
    esm = _bounded_1d_esm({"variable": "u", "kind": "neumann", "side": "xmax", "value": 0}, rules=())
    disc = spatial_discretize(esm, _GRAD)
    du = _eval_rhs(disc, "M", "u", range(1, 9))
    assert du[0] == -3.0 and du[7] == 1.0


def test_interface_ghost_matches_conformance_golden():
    """Interface BC lowering: the document's own interface rules (read here from
    the cross-binding golden's source) lower the BC `value` to the coupled-var
    ghost. Must match ``golden/interface_bc_lowering.json`` (Julia reference):
    u@xmax -> index(v,1), v@xmin -> index(u,4) (N=4 via bind_side_dim_size)."""
    repo = Path(__file__).resolve().parents[3]
    src = json.loads((repo / "tests/conformance/discretize/inputs/interface_bc_lowering.esm").read_text())
    golden = json.loads((repo / "tests/conformance/discretize/golden/interface_bc_lowering.json").read_text())
    want = {n: bc["value"] for n, bc in golden["models"]["M"]["boundary_conditions"].items()}

    rules = _bc_rules(src)                       # the interface rules from the document
    dims, dim_sizes = ["x"], {"x": 4}
    ctx = _bc_rule_ctx("g1", dims, dim_sizes, set(),
                       {"variables": {"u": {"type": "state"}, "v": {"type": "state"}}})
    got = {}
    for n, bc in src["models"]["M"]["boundary_conditions"].items():
        got[n] = _discretize_bc({**bc, "_name": n}, rules, ctx)
    assert got == want


def test_2d_corner_composes_per_axis_ghosts():
    """A 2-D Dirichlet corner cell is out-of-range on BOTH axes; the generic
    lowering splices a ghost per axis (no out-of-range read survives at (1,1))."""
    dx = 0.25
    lap = {"discretizations": {"d2": {"discretizations": {"c": {
        "applies_to": {"op": "d2", "args": ["$u"], "dim": "$x"}, "grid_family": "cartesian",
        "replacement": {"op": "arrayop", "output_idx": ["$x"], "args": ["$u"], "expr": {"op": "/", "args": [
            {"op": "+", "args": [
                {"op": "index", "args": ["$u", {"op": "+", "args": ["$x", -1]}]},
                {"op": "*", "args": [-2, {"op": "index", "args": ["$u", "$x"]}]},
                {"op": "index", "args": ["$u", {"op": "+", "args": ["$x", 1]}]}]},
            {"op": "*", "args": ["dx", "dx"]}]}}}}}}}
    esm = {"esm": "0.5.0", "metadata": {"name": "H"}, "rules": [_DIRICHLET],
        "domains": {"sq": {"independent_variable": "t",
            "spatial": {"x": {"min": 0.0, "max": 1.0, "grid_spacing": dx},
                        "y": {"min": 0.0, "max": 1.0, "grid_spacing": dx}},
            "boundary_conditions": [{"type": "dirichlet", "value": 0.0, "dimensions": ["x", "y"]}]}},
        "models": {"H": {"domain": "sq", "system_kind": "pde",
            "variables": {"u": {"type": "state", "units": "1"}},
            "equations": [{"lhs": {"op": "D", "args": ["u"], "wrt": "t"},
                           "rhs": {"op": "laplacian", "args": ["u"]}}]}}}
    disc = spatial_discretize(esm, lap)
    ma = _ma(disc, "H")
    n = int(round(1.0 / dx)) + 1
    # the corner cell (1,1) is a single-cell region; every read it makes lands
    # inside [1,N] on both axes (each out-of-range ghost spliced and reindexed).
    corner = next(v for r, v in zip(ma["regions"], ma["values"]) if r == [[1, 1], [1, 1]])
    reads = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("op") in ("laplacian", "grad", "d2"):
                raise AssertionError(f"undiscretized op {node['op']!r} survived in corner cell")
            if node.get("op") == "index" and node.get("args", [None])[0] == "u":
                reads.append(node["args"][1:])
            for a in node.get("args", []):
                walk(a)
        elif isinstance(node, list):
            for a in node:
                walk(a)
    walk(corner)
    assert reads, "corner cell makes no reads"
    for sub in reads:                          # every index concrete and in-range on both axes
        assert all(isinstance(k, int) and 1 <= k <= n for k in sub), sub
    # discretizes to a valid ODE that integrates.
    import earthsci_toolkit as et
    from earthsci_toolkit.simulation import simulate
    ic = {f"u[{i},{j}]": math.sin(math.pi * (i - 0.5) / n) * math.sin(math.pi * (j - 0.5) / n)
          for i in range(1, n + 1) for j in range(1, n + 1)}
    r = simulate(et.load(disc), (0.0, 0.01), initial_conditions=ic, method="LSODA",
                 rtol=1e-7, atol=1e-9)
    assert r.success

