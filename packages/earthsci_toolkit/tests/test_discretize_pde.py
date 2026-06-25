"""Method-of-lines PDE driver: discretize a continuous PDE and integrate it.

Exercises ``earthsci_toolkit.discretize_pde.discretize_pde`` end to end through
the canonical ``simulate`` ArrayOp path, validating against closed-form
solutions. These mirror the hand-authored conformance fixtures
``tests/fixtures/arrayop/15_discretized_1d_heat.esm`` and ``16_…2d_heat.esm``,
but produced from a *continuous* PDE spec by the driver rather than by hand.
"""

from __future__ import annotations

import math

import numpy as np

import earthsci_toolkit as et
from earthsci_toolkit.discretize_pde import discretize_pde
from earthsci_toolkit.simulation import simulate


def _heat(dims_spec, bc):
    """A continuous heat PDE: D(u)/dt = laplacian(u) on a Cartesian box."""
    return {
        "esm": "0.5.0",
        "metadata": {"name": "Heat"},
        "domains": {
            "box": {
                "independent_variable": "t",
                "spatial": dims_spec,
                "boundary_conditions": [bc],
            }
        },
        "models": {
            "Heat": {
                "domain": "box",
                "system_kind": "pde",
                "variables": {"u": {"type": "state", "units": "1"}},
                "equations": [
                    {
                        "lhs": {"op": "D", "args": ["u"], "wrt": "t"},
                        "rhs": {"op": "laplacian", "args": ["u"]},
                    }
                ],
            }
        },
    }


def _sample(result, key, t):
    idx = next(i for i, n in enumerate(result.vars) if n.endswith(key))
    return float(np.interp(t, result.t, result.y[idx]))


def test_1d_heat_dirichlet_matches_analytical():
    cont = _heat(
        {"x": {"min": 0.0, "max": 1.0, "grid_spacing": 0.2}},
        {"type": "dirichlet", "value": 0.0, "dimensions": ["x"]},
    )
    disc = discretize_pde(cont)
    assert disc["models"]["Heat"]["variables"]["u"]["shape"] == ["x"]
    rhs = disc["models"]["Heat"]["equations"][0]["rhs"]
    # interior + 2 ghost regions (xmin, xmax)
    assert len(rhs["expr"]["args"][0]["regions"]) == 3

    f = et.load(disc)
    ic = {f"u[{i}]": math.sin(math.pi * i / 5) for i in range(1, 5)}
    r = simulate(f, (0.0, 0.1), initial_conditions=ic, method="LSODA")
    assert r.success

    lam = (1 / 0.2**2) * (2 * math.cos(math.pi / 5) - 2)  # discrete eigenvalue
    for i in range(1, 5):
        want = math.exp(lam * 0.1) * math.sin(math.pi * i / 5)
        assert _sample(r, f"[{i}]", 0.1) == pytest_approx(want)


def test_2d_heat_dirichlet_matches_analytical():
    cont = _heat(
        {
            "x": {"min": 0.0, "max": 1.0, "grid_spacing": 0.25},
            "y": {"min": 0.0, "max": 1.0, "grid_spacing": 0.25},
        },
        {"type": "dirichlet", "value": 0.0, "dimensions": ["x", "y"]},
    )
    disc = discretize_pde(cont)
    assert disc["models"]["Heat"]["variables"]["u"]["shape"] == ["x", "y"]
    rhs = disc["models"]["Heat"]["equations"][0]["rhs"]
    assert len(rhs["expr"]["args"][0]["regions"]) == 9  # 3^2: interior+4 edges+4 corners

    f = et.load(disc)
    ic = {
        f"u[{i},{j}]": math.sin(i * math.pi / 4) * math.sin(j * math.pi / 4)
        for i in range(1, 4)
        for j in range(1, 4)
    }
    r = simulate(f, (0.0, 0.05), initial_conditions=ic, method="LSODA")
    assert r.success

    lam = 2 * 16 * (2 * math.cos(math.pi / 4) - 2)
    for i in range(1, 4):
        for j in range(1, 4):
            want = (
                math.exp(lam * 0.05)
                * math.sin(i * math.pi / 4)
                * math.sin(j * math.pi / 4)
            )
            assert _sample(r, f"[{i},{j}]", 0.05) == pytest_approx(want)


def test_neumann_preserves_a_constant_field():
    """Zero-gradient (reflecting) BCs: a uniform field has zero Laplacian
    everywhere and must not decay (Dirichlet-0 would bleed at the edges)."""
    cont = _heat(
        {"x": {"min": 0.0, "max": 1.0, "grid_spacing": 0.2}},
        {"type": "zero_gradient", "dimensions": ["x"]},
    )
    disc = discretize_pde(cont)
    # zero-gradient keeps both endpoints -> 6 interior nodes here
    assert disc["models"]["Heat"]["equations"][0]["rhs"]["ranges"]["x"] == [1, 6]

    f = et.load(disc)
    n = 6
    ic = {f"u[{i}]": 3.0 for i in range(1, n + 1)}
    r = simulate(f, (0.0, 1.0), initial_conditions=ic, method="LSODA")
    assert r.success
    for i in range(1, n + 1):
        assert _sample(r, f"[{i}]", 1.0) == pytest_approx(3.0)


def test_grad_lowers_to_centered_stencil():
    """A first-derivative operator lowers to the centered (u[x+1]-u[x-1])/2dx."""
    cont = {
        "esm": "0.5.0",
        "metadata": {"name": "Adv"},
        "domains": {
            "line": {
                "independent_variable": "t",
                "spatial": {"x": {"min": 0.0, "max": 1.0, "grid_spacing": 0.25}},
                "boundary_conditions": [
                    {"type": "dirichlet", "value": 0.0, "dimensions": ["x"]}
                ],
            }
        },
        "models": {
            "Adv": {
                "domain": "line",
                "system_kind": "pde",
                "variables": {"u": {"type": "state", "units": "1"}},
                "equations": [
                    {
                        "lhs": {"op": "D", "args": ["u"], "wrt": "t"},
                        "rhs": {"op": "grad", "args": ["u"], "dim": "x"},
                    }
                ],
            }
        },
    }
    disc = discretize_pde(cont)
    interior = disc["models"]["Adv"]["equations"][0]["rhs"]["expr"]["args"][0]["values"][0]
    # (u[x+1] - u[x-1]) / (2*0.25)
    assert interior["op"] == "/"
    assert interior["args"][1] == {"op": "*", "args": [2, 0.25]}
    diff = interior["args"][0]
    assert diff["op"] == "-"
    assert diff["args"][0] == {"op": "index", "args": ["u", {"op": "+", "args": ["x", 1]}]}
    assert diff["args"][1] == {"op": "index", "args": ["u", {"op": "-", "args": ["x", 1]}]}


# Local tolerance helper (avoid importing pytest at module import for clarity).
import pytest  # noqa: E402

pytest_approx = lambda v: pytest.approx(v, rel=1e-6, abs=1e-9)  # noqa: E731
