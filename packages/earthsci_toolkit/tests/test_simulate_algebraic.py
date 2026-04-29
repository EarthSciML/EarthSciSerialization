"""Tests for scalar algebraic-equation elimination in simulate() (esm-y3n).

A model may declare a state variable whose value is determined by an
algebraic equation ``v = body`` rather than by an ODE ``D(v, t) = …``. The
canonical Python simulation runner must:

* Substitute the algebraic body into every other equation that references
  the variable, so the integrator's RHS depends only on the differential
  states (the equivalent of MTK's structural_simplify scalar pass).
* Reconstruct the algebraic value at every output time so the
  SimulationResult exposes correct trajectories for both differential and
  algebraic state variables.
* Reject cyclic algebraic systems with a clear error message.
* Leave pure-ODE models numerically identical to the previous behaviour.
"""

import json

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
    Parameter,
    Reaction,
    ReactionSystem,
    Species,
)
from earthsci_toolkit.parse import load
from earthsci_toolkit.simulation import SimulationError, simulate


def _diameter_growth_model() -> EsmFile:
    """Build the Seinfeld & Pandis Fig. 13.2 / Eq. 13.11–13.13 model directly.

    The model has three state variables — ``D_p`` (ODE), ``A`` (algebraic),
    ``I_D`` (algebraic that references ``A`` and ``D_p``) — and exercises
    every part of the elimination pipeline.
    """
    variables = {
        "R_gas": ModelVariable(type="parameter", default=8.314),
        "T": ModelVariable(type="parameter", default=298.0),
        "D_diff": ModelVariable(type="parameter", default=1.0e-5),
        "M_i": ModelVariable(type="parameter", default=0.1),
        "ρ_p": ModelVariable(type="parameter", default=1000.0),
        "Δp": ModelVariable(type="parameter", default=1.0e-4),
        "D_p": ModelVariable(type="state", default=2.0e-7),
        "I_D": ModelVariable(type="state"),
        "A": ModelVariable(type="state"),
    }

    eq_dDp = Equation(
        lhs=ExprNode(op="D", args=["D_p"], wrt="t"),
        rhs="I_D",
    )
    eq_A = Equation(
        lhs="A",
        rhs=ExprNode(
            op="/",
            args=[
                ExprNode(op="*", args=[4, "D_diff", "M_i", "Δp"]),
                ExprNode(op="*", args=["R_gas", "T", "ρ_p"]),
            ],
        ),
    )
    eq_ID = Equation(
        lhs="I_D",
        rhs=ExprNode(op="/", args=["A", "D_p"]),
    )

    model = Model(
        name="DiameterGrowthRate",
        variables=variables,
        equations=[eq_dDp, eq_A, eq_ID],
    )
    return EsmFile(
        version="0.1.0",
        metadata=Metadata(title="DiameterGrowthRate"),
        models={"DiameterGrowthRate": model},
    )


def test_simulate_eliminates_algebraic_states_diameter_growth():
    """``D_p[end]`` must be within 1% of the analytical 6.538e-7 m target."""
    file = _diameter_growth_model()
    result = simulate(
        file,
        tspan=(0.0, 1200.0),
        parameters={},
        initial_conditions={"D_p": 2.0e-7},
        method="LSODA",
    )
    assert result.success, f"simulate() failed: {result.message}"

    dp_idx = result.vars.index("DiameterGrowthRate.D_p")
    final_dp = result.y[dp_idx, -1]
    expected = 6.538165842082e-7
    rel_err = abs(final_dp - expected) / expected
    assert rel_err < 0.01, (
        f"D_p(t=1200) = {final_dp:.6e}, expected {expected:.6e} "
        f"(rel err {rel_err:.3%})"
    )


def test_simulate_recovers_algebraic_values_at_output():
    """Algebraic states must track their formula along the trajectory."""
    file = _diameter_growth_model()
    result = simulate(
        file,
        tspan=(0.0, 1200.0),
        parameters={},
        initial_conditions={"D_p": 2.0e-7},
        method="LSODA",
    )
    assert result.success

    a_idx = result.vars.index("DiameterGrowthRate.A")
    id_idx = result.vars.index("DiameterGrowthRate.I_D")
    dp_idx = result.vars.index("DiameterGrowthRate.D_p")

    # A is constant (depends only on parameters): every sample equals the
    # closed-form value within solver round-off.
    expected_A = 4 * 1.0e-5 * 0.1 * 1.0e-4 / (8.314 * 298.0 * 1000.0)
    assert np.allclose(result.y[a_idx, :], expected_A, rtol=1e-10, atol=0.0)

    # I_D = A / D_p must hold pointwise.
    expected_id = expected_A / result.y[dp_idx, :]
    assert np.allclose(result.y[id_idx, :], expected_id, rtol=1e-10, atol=0.0)


def test_simulate_rejects_cyclic_algebraic_equations():
    """A self-referential / mutually-cyclic algebraic system must error out."""
    variables = {
        "X": ModelVariable(type="state", default=0.0),
        "Y": ModelVariable(type="state", default=0.0),
        "Z": ModelVariable(type="state", default=0.0),
    }
    eq_dz = Equation(
        lhs=ExprNode(op="D", args=["Z"], wrt="t"),
        rhs=1.0,
    )
    eq_x = Equation(lhs="X", rhs=ExprNode(op="+", args=["Y", 1.0]))
    eq_y = Equation(lhs="Y", rhs=ExprNode(op="+", args=["X", 1.0]))

    model = Model(
        name="Cyclic",
        variables=variables,
        equations=[eq_dz, eq_x, eq_y],
    )
    file = EsmFile(
        version="0.1.0",
        metadata=Metadata(title="Cyclic"),
        models={"Cyclic": model},
    )

    result = simulate(
        file,
        tspan=(0.0, 1.0),
        parameters={},
        initial_conditions={},
        method="LSODA",
    )
    assert not result.success
    assert "Cyclic algebraic equations detected" in result.message


def test_simulate_pure_ode_model_unaffected_by_algebraic_pass():
    """A reaction system with no algebraic equations must integrate as before."""
    species_a = Species(name="A", default=1.0)
    species_b = Species(name="B", default=0.0)
    k = Parameter(name="k", value=0.5)
    reaction = Reaction(
        name="decay",
        reactants={"A": 1.0},
        products={"B": 1.0},
        rate_constant=0.5,
    )
    rs = ReactionSystem(
        name="Decay",
        species=[species_a, species_b],
        parameters=[k],
        reactions=[reaction],
    )
    file = EsmFile(
        version="0.1.0",
        metadata=Metadata(title="decay"),
        reaction_systems={"Decay": rs},
    )

    result = simulate(
        file,
        tspan=(0.0, 5.0),
        parameters={},
        initial_conditions={"A": 1.0, "B": 0.0},
        method="RK45",
    )
    assert result.success, f"simulate() failed: {result.message}"

    a_idx = result.vars.index("Decay.A")
    b_idx = result.vars.index("Decay.B")
    total = result.y[a_idx, :] + result.y[b_idx, :]
    assert np.allclose(total, 1.0, atol=1e-5)
    # Closed-form decay: A(t) = exp(-k t).
    assert np.isclose(result.y[a_idx, -1], np.exp(-0.5 * 5.0), rtol=1e-3)
