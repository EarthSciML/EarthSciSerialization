"""Tests for the 1D stencil walker kernels (esm-ga7, RFC §5.2.8).

Mirrors the Julia ``apply_stencil_ghosted_1d`` coverage in
``packages/EarthSciSerialization.jl/test/mms_evaluator_test.jl`` so the two
bindings agree on closed-set boundary_policy semantics, alias handling,
and the ``E_GHOST_*`` error paths.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from earthsci_toolkit.mms_evaluator import (
    MMSEvaluatorError,
    apply_stencil_ghosted_1d,
    apply_stencil_periodic_1d,
    eval_coeff,
)


# Centered 2nd-order finite difference: stencil = (-1/(2dx), 0, +1/(2dx))
# at offsets ±1. Used as the carrier for every boundary_policy below.
def _centered_fd_stencil():
    return [
        {
            "selector": {"kind": "cartesian", "axis": "x", "offset": -1},
            "coeff": {"op": "/", "args": [-1, {"op": "*", "args": [2, "dx"]}]},
        },
        {
            "selector": {"kind": "cartesian", "axis": "x", "offset": 1},
            "coeff": {"op": "/", "args": [1, {"op": "*", "args": [2, "dx"]}]},
        },
    ]


def _wide_stencil_4th():
    # 4th-order centered FD: (1, -8, 8, -1) / (12 dx) at offsets (-2, -1, 1, 2).
    return [
        {
            "selector": {"kind": "cartesian", "axis": "x", "offset": -2},
            "coeff": {"op": "/", "args": [1, {"op": "*", "args": [12, "dx"]}]},
        },
        {
            "selector": {"kind": "cartesian", "axis": "x", "offset": -1},
            "coeff": {"op": "/", "args": [-8, {"op": "*", "args": [12, "dx"]}]},
        },
        {
            "selector": {"kind": "cartesian", "axis": "x", "offset": 1},
            "coeff": {"op": "/", "args": [8, {"op": "*", "args": [12, "dx"]}]},
        },
        {
            "selector": {"kind": "cartesian", "axis": "x", "offset": 2},
            "coeff": {"op": "/", "args": [-1, {"op": "*", "args": [12, "dx"]}]},
        },
    ]


def test_eval_coeff_passthrough_to_evaluate():
    bindings = {"dx": 0.25}
    assert eval_coeff(0.5, bindings) == 0.5
    assert eval_coeff("dx", bindings) == 0.25
    assert eval_coeff(
        {"op": "/", "args": [1, {"op": "*", "args": [2, "dx"]}]},
        bindings,
    ) == pytest.approx(1.0 / 0.5)


def test_periodic_kind_byte_equal_to_periodic_walker():
    n = 32
    dx = 1.0 / n
    u = np.array([math.sin(2 * math.pi * (i + 0.5) * dx) for i in range(n)])
    bindings = {"dx": dx}
    stencil = _centered_fd_stencil()
    ref = apply_stencil_periodic_1d(stencil, u, bindings)
    for Ng in (1, 2, 5):
        got = apply_stencil_ghosted_1d(
            stencil, u, bindings,
            ghost_width=Ng, boundary_policy="periodic",
        )
        np.testing.assert_array_equal(got, ref)


def test_reflecting_zero_flux_at_boundary_on_symmetric_profile():
    # u = cos(pi x) on [0,1] cell-centers. Reflecting fill makes the
    # centered FD reduce to a one-sided forward / backward difference at
    # the edges and exposes interior accuracy elsewhere.
    n = 16
    dx = 1.0 / n
    u = np.array([math.cos(math.pi * (i + 0.5) * dx) for i in range(n)])
    bindings = {"dx": dx}
    got = apply_stencil_ghosted_1d(
        _centered_fd_stencil(), u, bindings,
        ghost_width=1, boundary_policy="reflecting",
    )
    assert got[0] == pytest.approx((u[1] - u[0]) / (2 * dx), abs=1e-12)
    assert got[-1] == pytest.approx((u[-1] - u[-2]) / (2 * dx), abs=1e-12)
    ref = np.array([-math.pi * math.sin(math.pi * (i + 0.5) * dx) for i in range(n)])
    interior = slice(2, n - 2)
    assert np.max(np.abs(got[interior] - ref[interior])) < 0.05


def test_neumann_zero_alias_matches_reflecting():
    n = 8
    dx = 1.0 / n
    u = np.arange(1.0, n + 1.0)
    bindings = {"dx": dx}
    via_reflecting = apply_stencil_ghosted_1d(
        _centered_fd_stencil(), u, bindings,
        ghost_width=1, boundary_policy="reflecting",
    )
    via_neumann = apply_stencil_ghosted_1d(
        _centered_fd_stencil(), u, bindings,
        ghost_width=1, boundary_policy="neumann_zero",
    )
    np.testing.assert_array_equal(via_neumann, via_reflecting)


def test_one_sided_extrapolation_linear_default_exact_on_linear_profile():
    n = 12
    dx = 0.1
    u = np.array([2.0 + 3.0 * (i + 1) for i in range(n)])
    bindings = {"dx": dx}
    got = apply_stencil_ghosted_1d(
        _centered_fd_stencil(), u, bindings,
        ghost_width=1, boundary_policy="one_sided_extrapolation",
    )
    np.testing.assert_allclose(got, np.full(n, 3.0 / dx), atol=1e-10)


def test_one_sided_extrapolation_degree2_exact_on_quadratic_profile():
    n = 10
    dx = 0.5
    u = np.array([float(i + 1) ** 2 for i in range(n)])
    bindings = {"dx": dx}
    got = apply_stencil_ghosted_1d(
        _centered_fd_stencil(), u, bindings,
        ghost_width=1,
        boundary_policy={"kind": "one_sided_extrapolation", "degree": 2},
    )
    # Centered FD on i^2 at cell index i: ((i+1)^2 - (i-1)^2)/(2dx) = 4i/(2dx).
    ref = np.array([2.0 * (i + 1) / dx for i in range(n)])
    np.testing.assert_allclose(got, ref, atol=1e-10)


def test_one_sided_extrapolation_degree3_exact_on_cubic_profile():
    n = 12
    dx = 0.25
    u = np.array([float(i + 1) ** 3 for i in range(n)])
    bindings = {"dx": dx}
    got = apply_stencil_ghosted_1d(
        _centered_fd_stencil(), u, bindings,
        ghost_width=1,
        boundary_policy={"kind": "one_sided_extrapolation", "degree": 3},
    )
    ref = np.array([(6.0 * (i + 1) ** 2 + 2.0) / (2.0 * dx) for i in range(n)])
    np.testing.assert_allclose(got, ref, atol=1e-10)


def test_extrapolate_alias_defaults_to_degree1():
    n = 8
    dx = 0.1
    u = np.array([1.5 * (i + 1) + 0.5 for i in range(n)])
    bindings = {"dx": dx}
    got = apply_stencil_ghosted_1d(
        _centered_fd_stencil(), u, bindings,
        ghost_width=1, boundary_policy="extrapolate",
    )
    np.testing.assert_allclose(got, np.full(n, 1.5 / dx), atol=1e-10)


def test_one_sided_extrapolation_degree0_constant_fill():
    # degree=0 — Neumann-zero-style constant ghost. Centered FD then sees
    # u[0] on both sides at the left boundary, so the derivative is
    # (u[1] - u[0]) / (2 dx).
    n = 6
    dx = 0.1
    u = np.array([1.0, 4.0, 9.0, 16.0, 25.0, 36.0])
    bindings = {"dx": dx}
    got = apply_stencil_ghosted_1d(
        _centered_fd_stencil(), u, bindings,
        ghost_width=1,
        boundary_policy={"kind": "one_sided_extrapolation", "degree": 0},
    )
    assert got[0] == pytest.approx((u[1] - u[0]) / (2 * dx))
    assert got[-1] == pytest.approx((u[-1] - u[-2]) / (2 * dx))


def test_prescribed_caller_supplied_ghost_values():
    n = 8
    dx = 0.1
    u = np.arange(1.0, n + 1.0)  # u[i] = i+1 in 0-indexed → cell i+1 in 1-indexed
    bindings = {"dx": dx}
    calls = []

    def prescribe(side, k):
        calls.append((side, k))
        # supply linear extension u[i] = i (1-indexed cell index)
        return float(1 - k) if side == "left" else float(n + k)

    got = apply_stencil_ghosted_1d(
        _centered_fd_stencil(), u, bindings,
        ghost_width=1, boundary_policy="prescribed", prescribe=prescribe,
    )
    np.testing.assert_allclose(got, np.full(n, 1.0 / dx), atol=1e-10)
    assert ("left", 1) in calls
    assert ("right", 1) in calls


def test_ghosted_alias_requires_prescribe():
    # `ghosted` is the v0.3.x alias for `prescribed` and inherits the same
    # required-callback contract.
    n = 8
    dx = 0.1
    u = np.arange(1.0, n + 1.0)
    bindings = {"dx": dx}
    with pytest.raises(MMSEvaluatorError) as excinfo:
        apply_stencil_ghosted_1d(
            _centered_fd_stencil(), u, bindings,
            ghost_width=1, boundary_policy="ghosted",
        )
    assert excinfo.value.code == "E_MMS_BAD_FIXTURE"


def test_ghost_width_too_small_for_stencil_offset():
    n = 16
    dx = 1.0 / n
    u = np.array([math.sin(2 * math.pi * (i + 0.5) * dx) for i in range(n)])
    bindings = {"dx": dx}
    with pytest.raises(MMSEvaluatorError) as excinfo:
        apply_stencil_ghosted_1d(
            _wide_stencil_4th(), u, bindings,
            ghost_width=1, boundary_policy="periodic",
        )
    assert excinfo.value.code == "E_GHOST_WIDTH_TOO_SMALL"


def test_panel_dispatch_recognised_but_unsupported():
    n = 8
    dx = 0.1
    u = np.arange(1.0, n + 1.0)
    bindings = {"dx": dx}
    with pytest.raises(MMSEvaluatorError) as excinfo:
        apply_stencil_ghosted_1d(
            _centered_fd_stencil(), u, bindings,
            ghost_width=1,
            boundary_policy={
                "kind": "panel_dispatch",
                "interior": "dist",
                "boundary": "dist_bnd",
            },
        )
    assert excinfo.value.code == "E_GHOST_FILL_UNSUPPORTED"


def test_unknown_boundary_policy_kind_rejected():
    n = 8
    dx = 0.1
    u = np.arange(1.0, n + 1.0)
    bindings = {"dx": dx}
    with pytest.raises(MMSEvaluatorError) as excinfo:
        apply_stencil_ghosted_1d(
            _centered_fd_stencil(), u, bindings,
            ghost_width=1, boundary_policy="not_a_real_kind",
        )
    assert excinfo.value.code == "E_MMS_BAD_FIXTURE"


def test_negative_ghost_width_rejected():
    n = 8
    dx = 0.1
    u = np.arange(1.0, n + 1.0)
    bindings = {"dx": dx}
    with pytest.raises(MMSEvaluatorError) as excinfo:
        apply_stencil_ghosted_1d(
            _centered_fd_stencil(), u, bindings,
            ghost_width=-1, boundary_policy="periodic",
        )
    assert excinfo.value.code == "E_MMS_BAD_FIXTURE"


def test_boundary_policy_dict_missing_kind_rejected():
    n = 8
    dx = 0.1
    u = np.arange(1.0, n + 1.0)
    bindings = {"dx": dx}
    with pytest.raises(MMSEvaluatorError) as excinfo:
        apply_stencil_ghosted_1d(
            _centered_fd_stencil(), u, bindings,
            ghost_width=1, boundary_policy={"degree": 2},
        )
    assert excinfo.value.code == "E_MMS_BAD_FIXTURE"


def test_periodic_walker_centered_fd_recovers_cosine():
    # Smoke-test the underlying periodic walker: centered FD on sin(2πx)
    # should converge to 2π cos(2πx) at cell centers.
    n = 64
    dx = 1.0 / n
    u = np.array([math.sin(2 * math.pi * (i + 0.5) * dx) for i in range(n)])
    ref = np.array([2 * math.pi * math.cos(2 * math.pi * (i + 0.5) * dx)
                    for i in range(n)])
    got = apply_stencil_periodic_1d(_centered_fd_stencil(), u, {"dx": dx})
    # Centered 2nd FD has O(dx^2) leading error; n=64 is comfortably below 0.1.
    assert np.max(np.abs(got - ref)) < 0.05


def test_substencil_resolution_rejects_missing_selection():
    multi = {
        "left_edge": _centered_fd_stencil(),
        "right_edge": _centered_fd_stencil(),
    }
    u = np.arange(1.0, 9.0)
    with pytest.raises(MMSEvaluatorError) as excinfo:
        apply_stencil_periodic_1d(multi, u, {"dx": 0.1})
    assert excinfo.value.code == "E_MMS_BAD_FIXTURE"


def test_substencil_resolution_rejects_unknown_selection():
    multi = {
        "left_edge": _centered_fd_stencil(),
    }
    u = np.arange(1.0, 9.0)
    with pytest.raises(MMSEvaluatorError) as excinfo:
        apply_stencil_periodic_1d(multi, u, {"dx": 0.1},
                                  sub_stencil="right_edge")
    assert excinfo.value.code == "E_MMS_BAD_FIXTURE"


def test_substencil_unexpected_on_single_stencil_rejected():
    u = np.arange(1.0, 9.0)
    with pytest.raises(MMSEvaluatorError) as excinfo:
        apply_stencil_periodic_1d(_centered_fd_stencil(), u, {"dx": 0.1},
                                  sub_stencil="left_edge")
    assert excinfo.value.code == "E_MMS_BAD_FIXTURE"
