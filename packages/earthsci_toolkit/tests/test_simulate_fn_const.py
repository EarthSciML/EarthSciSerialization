"""Regression tests for `fn` / `const` op support in the SymPy simulation path (esm-nsc).

fastjx.esm and any model authoring an ``interp.linear`` / ``interp.bilinear``
observed body routes through ``earthsci_toolkit.sympy_bridge`` (no array op
in the equations triggers the SymPy + lambdify pipeline rather than the
NumPy interpreter). These tests drive ``simulate()`` end-to-end on small
inline-``const`` models so the regression covers the canonical
``load → simulate`` pipeline:

* a 1-D ``interp.linear`` photolysis rate driving an ODE — exercises the
  ``fn`` / ``const`` path inside the integrator's RHS,
* a 2-D ``interp.bilinear`` table driving an observed body — exercises the
  per-output observed-vector lambdify path with array runtime inputs.
"""

import numpy as np
import pytest

pytest.importorskip("scipy")
pytest.importorskip("sympy")

from earthsci_toolkit.esm_types import (
    EsmFile,
    Equation,
    ExprNode,
    Metadata,
    Model,
    ModelVariable,
)
from earthsci_toolkit.simulation import simulate


def _interp_linear_photolysis_model() -> EsmFile:
    """1-state ODE ``D(C, t) = -k(T) * C`` with ``k(T)`` an ``interp.linear``.

    The table is monotonic in ``T`` (a stand-in for a temperature-dependent
    photolysis quantum yield); evaluating at a fixed parameter value gives a
    closed-form exponential decay against which the simulator can be
    compared bit-for-bit.
    """
    table = ExprNode(op="const", args=[], value=[1.0e-3, 2.0e-3, 4.0e-3])
    axis = ExprNode(op="const", args=[], value=[270.0, 290.0, 310.0])
    rate = ExprNode(op="fn", name="interp.linear", args=[table, axis, "T"])

    variables = {
        "T": ModelVariable(type="parameter", default=290.0),
        "C": ModelVariable(type="state", default=1.0),
        "k": ModelVariable(type="observed", expression=rate),
    }
    eq_dC = Equation(
        lhs=ExprNode(op="D", args=["C"], wrt="t"),
        rhs=ExprNode(op="*", args=[-1.0, "k", "C"]),
    )
    eq_k = Equation(lhs="k", rhs=rate)

    return EsmFile(
        version="0.1.0",
        metadata=Metadata(title="InterpLinearPhotolysis"),
        models={
            "Photolysis": Model(
                name="Photolysis",
                variables=variables,
                equations=[eq_dC, eq_k],
            )
        },
    )


def test_simulate_interp_linear_drives_rhs():
    """``D(C, t) = -interp.linear(table, axis, T) * C`` integrates correctly.

    At ``T = 290`` the interp.linear value equals exactly the table's
    midpoint entry (``2.0e-3``) so the analytical solution is
    ``C(t) = exp(-2.0e-3 * t)``.
    """
    file = _interp_linear_photolysis_model()
    result = simulate(
        file,
        tspan=(0.0, 500.0),
        parameters={"T": 290.0},
        initial_conditions={"C": 1.0},
        method="LSODA",
    )
    assert result.success, f"simulate() failed: {result.message}"

    c_idx = result.vars.index("Photolysis.C")
    expected = np.exp(-2.0e-3 * result.t)
    np.testing.assert_allclose(result.y[c_idx, :], expected, rtol=1e-6, atol=1e-8)


def test_simulate_interp_linear_observed_recovered():
    """The observed ``k`` body must be returned in the result vector with
    the constant interpolated value over the entire output time grid."""
    file = _interp_linear_photolysis_model()
    result = simulate(
        file,
        tspan=(0.0, 100.0),
        parameters={"T": 290.0},
        initial_conditions={"C": 1.0},
        method="LSODA",
    )
    assert result.success

    k_idx = result.vars.index("Photolysis.k")
    assert np.allclose(result.y[k_idx, :], 2.0e-3, rtol=1e-12, atol=0.0)


def _interp_bilinear_observed_model() -> EsmFile:
    """``F(P, cosSZA) = interp.bilinear(table, P_axis, cosSZA_axis, P, cosSZA)``.

    No state variables — only an observed body — so the simulate() observed-
    only pathway is exercised on the synthetic time grid.
    """
    table = ExprNode(
        op="const",
        args=[],
        value=[
            [0.0, 1.0, 2.0],
            [10.0, 11.0, 12.0],
        ],
    )
    axis_p = ExprNode(op="const", args=[], value=[80000.0, 100000.0])
    axis_cos = ExprNode(op="const", args=[], value=[0.0, 0.5, 1.0])
    rate = ExprNode(
        op="fn",
        name="interp.bilinear",
        args=[table, axis_p, axis_cos, "P", "cosSZA"],
    )

    variables = {
        "P": ModelVariable(type="parameter", default=90000.0),
        "cosSZA": ModelVariable(type="parameter", default=0.5),
        "F": ModelVariable(type="observed", expression=rate),
    }
    eq_F = Equation(lhs="F", rhs=rate)

    return EsmFile(
        version="0.1.0",
        metadata=Metadata(title="InterpBilinearObserved"),
        models={
            "Flux": Model(
                name="Flux",
                variables=variables,
                equations=[eq_F],
            )
        },
    )


def test_simulate_interp_bilinear_observed_only():
    """An observed-only model with an ``interp.bilinear`` body must return
    the bit-equivalent interpolated value over the synthetic time grid."""
    file = _interp_bilinear_observed_model()
    result = simulate(
        file,
        tspan=(0.0, 1.0),
        parameters={"P": 90000.0, "cosSZA": 0.5},
        initial_conditions={},
    )
    assert result.success, f"simulate() failed: {result.message}"

    f_idx = result.vars.index("Flux.F")
    # Bilinear at (P=90000, cosSZA=0.5): row blend at P → (5.0, 6.0, 7.0); the
    # cosSZA axis hits the interior knot at index 1 so the result equals 6.0.
    assert np.allclose(result.y[f_idx, :], 6.0, rtol=1e-12, atol=0.0)
