"""Tests for the coupled-system flattening implementation."""

import pytest

from earthsci_toolkit.flatten import flatten
from earthsci_toolkit.esm_types import (
    EsmFile,
    Metadata,
    Model,
    ModelVariable,
    Equation,
    ExprNode,
    ReactionSystem,
    Species,
    Parameter,
    VariableMapCoupling,
)


def _make_metadata() -> Metadata:
    return Metadata(title="test")


def _empty_file(**kwargs) -> EsmFile:
    base = dict(version="0.1.0", metadata=_make_metadata())
    base.update(kwargs)
    return EsmFile(**base)


def test_flatten_empty_raises():
    file = _empty_file()
    with pytest.raises(ValueError):
        flatten(file)


def test_flatten_single_model_namespaces_variables():
    var_T = ModelVariable(type="state", units="K", default=300.0,
                          description="Temperature")
    var_k = ModelVariable(type="parameter", default=0.1)
    eq = Equation(
        lhs=ExprNode(op="D", args=["T"], wrt="t"),
        rhs=ExprNode(op="*", args=["k", "T"]),
    )
    model = Model(name="Atmos",
                  variables={"T": var_T, "k": var_k},
                  equations=[eq])

    file = _empty_file(models={"Atmos": model})

    flat = flatten(file)
    assert "Atmos.T" in flat.state_variables
    assert "Atmos.k" in flat.parameters
    assert flat.metadata.source_systems == ["Atmos"]
    assert len(flat.equations) == 1
    eq0 = flat.equations[0]
    assert eq0.source_system == "Atmos"
    assert "Atmos.T" in eq0.lhs
    assert "Atmos.k" in eq0.rhs
    assert "Atmos.T" in eq0.rhs


def test_flatten_reaction_system_namespaces_species_and_params():
    species = Species(name="O3", units="mol/L", default=1e-6)
    param = Parameter(name="k1", value=0.1, units="1/s")
    rs = ReactionSystem(name="Chem", species=[species], parameters=[param])

    file = _empty_file(reaction_systems={"Chem": rs})

    flat = flatten(file)
    assert "Chem.O3" in flat.state_variables
    assert "Chem.k1" in flat.parameters
    assert flat.metadata.source_systems == ["Chem"]


def test_flatten_records_coupling_rules():
    var_x = ModelVariable(type="state")
    var_y = ModelVariable(type="parameter")
    model_a = Model(name="A", variables={"x": var_x})
    model_b = Model(name="B", variables={"y": var_y})

    coupling = VariableMapCoupling(
        from_var="A.x", to_var="B.y", transform="identity",
    )

    file = _empty_file(models={"A": model_a, "B": model_b},
                       coupling=[coupling])

    flat = flatten(file)
    assert any("variable_map" in r for r in flat.metadata.coupling_rules)


def test_flatten_recurses_into_subsystems():
    inner_var = ModelVariable(type="state")
    inner = Model(name="Inner", variables={"x": inner_var})
    outer_var = ModelVariable(type="state")
    outer = Model(name="Outer",
                  variables={"y": outer_var},
                  subsystems={"Inner": inner})

    file = _empty_file(models={"Outer": outer})

    flat = flatten(file)
    assert "Outer.y" in flat.state_variables
    assert "Outer.Inner.x" in flat.state_variables
