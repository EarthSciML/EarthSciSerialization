"""End-to-end tests for simulate() consuming a FlattenedSystem.

These cover the new spec-§4.7.5 contract: simulate() routes through flatten()
and rejects PDE inputs with UnsupportedDimensionalityError.
"""

import numpy as np
import pytest

pytest.importorskip("scipy")  # the simulate path requires scipy

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
from earthsci_toolkit.flatten import (
    FlattenedSystem,
    UnsupportedDimensionalityError,
    flatten,
)
from earthsci_toolkit.simulation import simulate


def _metadata() -> Metadata:
    return Metadata(title="test")


def _decay_file() -> EsmFile:
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
    return EsmFile(version="0.1.0", metadata=_metadata(), reaction_systems={"Decay": rs})


# ----------------------------------------------------------------------------
# simulate(esm_file) routes through flatten()
# ----------------------------------------------------------------------------


def test_simulate_esm_file_runs_through_flatten():
    file = _decay_file()
    result = simulate(
        file,
        tspan=(0.0, 5.0),
        parameters={},
        initial_conditions={"A": 1.0, "B": 0.0},
        method="RK45",
    )
    assert result.success, f"simulate() failed: {result.message}"
    # State variables are dot-namespaced.
    assert "Decay.A" in result.vars
    assert "Decay.B" in result.vars
    a_idx = result.vars.index("Decay.A")
    b_idx = result.vars.index("Decay.B")
    # A decays, B grows, mass is conserved.
    assert result.y[a_idx, -1] < result.y[a_idx, 0]
    assert result.y[b_idx, -1] > result.y[b_idx, 0]
    total = result.y[a_idx, :] + result.y[b_idx, :]
    assert np.allclose(total, 1.0, atol=1e-5)


# ----------------------------------------------------------------------------
# simulate(flatten(esm_file)) gives the same result
# ----------------------------------------------------------------------------


def test_simulate_flatten_round_trip_matches_esm_file_path():
    file = _decay_file()
    initial = {"A": 1.0, "B": 0.0}

    via_file = simulate(file, tspan=(0.0, 5.0), parameters={},
                        initial_conditions=initial, method="RK45")
    via_flat = simulate(flatten(file), tspan=(0.0, 5.0), parameters={},
                        initial_conditions=initial, method="RK45")

    assert via_file.success and via_flat.success
    assert via_file.vars == via_flat.vars
    # Same final state to numerical tolerance — both paths use the same RHS.
    assert np.allclose(via_file.y[:, -1], via_flat.y[:, -1], atol=1e-9)


# ----------------------------------------------------------------------------
# PDE rejection: simulate() raises on spatial independent variables
# ----------------------------------------------------------------------------


def test_simulate_rejects_pde_systems():
    """A model with grad operators should raise UnsupportedDimensionalityError."""
    var_u = ModelVariable(type="state", default=0.0)
    eq = Equation(
        lhs=ExprNode(op="D", args=["u"], wrt="t"),
        rhs=ExprNode(op="grad", args=["u"], dim="x"),
    )
    model = Model(name="Adv", variables={"u": var_u}, equations=[eq])
    file = EsmFile(version="0.1.0", metadata=_metadata(), models={"Adv": model})

    with pytest.raises(UnsupportedDimensionalityError) as excinfo:
        simulate(file, tspan=(0.0, 1.0))

    msg = str(excinfo.value)
    assert "spatial" in msg.lower()
    assert "PDE" in msg or "PDE-capable" in msg


# ----------------------------------------------------------------------------
# Models with explicit ODEs (no reaction system) work
# ----------------------------------------------------------------------------


def test_simulate_works_for_pure_ode_model():
    """A Model with explicit equations (no reactions) should run end-to-end."""
    var_x = ModelVariable(type="state", default=2.0)
    var_k = ModelVariable(type="parameter", default=0.3)
    eq = Equation(
        lhs=ExprNode(op="D", args=["x"], wrt="t"),
        rhs=ExprNode(op="*", args=[ExprNode(op="-", args=["k"]), "x"]),
    )
    model = Model(name="Decay", variables={"x": var_x, "k": var_k}, equations=[eq])
    file = EsmFile(version="0.1.0", metadata=_metadata(), models={"Decay": model})

    result = simulate(
        file,
        tspan=(0.0, 5.0),
        initial_conditions={"x": 2.0},
        method="RK45",
    )
    assert result.success, f"simulate() failed: {result.message}"
    idx = result.vars.index("Decay.x")
    # Analytical solution: x(t) = 2*exp(-0.3*t); at t=5 → 2*exp(-1.5) ≈ 0.4463.
    assert abs(result.y[idx, -1] - 2.0 * np.exp(-1.5)) < 1e-3
