"""Tests for the parse module."""

import json
import pytest
import jsonschema

from esm_format import load
from esm_format.parse import _parse_expression
from esm_format.serialize import _serialize_expression
from esm_format.types import ExprNode, EsmFile


def test_load_invalid_json():
    """Test that invalid JSON raises JSONDecodeError."""
    invalid_json = '{"invalid": json,}'
    with pytest.raises(json.JSONDecodeError):
        load(invalid_json)


def test_load_invalid_schema():
    """Test that JSON not matching schema raises ValidationError."""
    invalid_esm = '{"invalid": "schema"}'
    with pytest.raises(jsonschema.ValidationError):
        load(invalid_esm)


def test_parse_simple_expression():
    """Test parsing of simple expressions."""
    # Test number
    assert _parse_expression(42) == 42
    assert _parse_expression(3.14) == 3.14

    # Test string
    assert _parse_expression("x") == "x"

    # Test expression node
    expr_data = {
        "op": "+",
        "args": [1, 2]
    }
    expr = _parse_expression(expr_data)
    assert isinstance(expr, ExprNode)
    assert expr.op == "+"
    assert expr.args == [1, 2]


def test_parse_nested_expression():
    """Test parsing of nested expressions."""
    expr_data = {
        "op": "*",
        "args": [
            {
                "op": "+",
                "args": ["x", 1]
            },
            2
        ]
    }
    expr = _parse_expression(expr_data)
    assert isinstance(expr, ExprNode)
    assert expr.op == "*"
    assert len(expr.args) == 2
    assert expr.args[1] == 2

    nested_expr = expr.args[0]
    assert isinstance(nested_expr, ExprNode)
    assert nested_expr.op == "+"
    assert nested_expr.args == ["x", 1]


def test_load_minimal_valid_esm():
    """Test loading a minimal valid ESM file."""
    minimal_esm = {
        "esm": "0.1.0",
        "metadata": {
            "name": "Test Model"
        },
        "models": {
            "test_model": {
                "variables": {
                    "x": {
                        "type": "state"
                    }
                },
                "equations": [
                    {
                        "lhs": "x",
                        "rhs": 1
                    }
                ]
            }
        }
    }

    json_str = json.dumps(minimal_esm)
    esm_file = load(json_str)

    assert isinstance(esm_file, EsmFile)
    assert esm_file.version == "0.1.0"
    assert esm_file.metadata.title == "Test Model"
    assert len(esm_file.models) == 1

    model = esm_file.models[0]
    assert model.name == "test_model"
    assert len(model.variables) == 1
    assert "x" in model.variables
    assert model.variables["x"].type == "state"
    assert len(model.equations) == 1


def test_load_reaction_system():
    """Test loading an ESM file with reaction system."""
    rs_esm = {
        "esm": "0.1.0",
        "metadata": {
            "name": "Reaction Test"
        },
        "reaction_systems": {
            "test_reactions": {
                "species": {
                    "A": {"units": "mol"},
                    "B": {"units": "mol"},
                    "C": {"units": "mol"}
                },
                "parameters": {
                    "k1": {"units": "1/s", "default": 0.1}
                },
                "reactions": [
                    {
                        "id": "R1",
                        "name": "A + B -> C",
                        "substrates": [
                            {"species": "A", "stoichiometry": 1},
                            {"species": "B", "stoichiometry": 1}
                        ],
                        "products": [
                            {"species": "C", "stoichiometry": 1}
                        ],
                        "rate": "k1"
                    }
                ]
            }
        }
    }

    json_str = json.dumps(rs_esm)
    esm_file = load(json_str)

    assert len(esm_file.reaction_systems) == 1
    rs = esm_file.reaction_systems[0]
    assert rs.name == "test_reactions"

    # Check species
    assert len(rs.species) == 3
    species_names = [sp.name for sp in rs.species]
    assert "A" in species_names
    assert "B" in species_names
    assert "C" in species_names

    # Check parameters
    assert len(rs.parameters) == 1
    param = rs.parameters[0]
    assert param.name == "k1"
    assert param.units == "1/s"
    assert param.value == 0.1

    # Check reactions
    assert len(rs.reactions) == 1
    reaction = rs.reactions[0]
    assert reaction.name == "A + B -> C"
    assert reaction.reactants == {"A": 1.0, "B": 1.0}
    assert reaction.products == {"C": 1.0}


def test_expression_with_metadata():
    """Test parsing expressions with wrt and dim metadata."""
    expr_data = {
        "op": "D",
        "args": ["x"],
        "wrt": "t"
    }
    expr = _parse_expression(expr_data)
    assert isinstance(expr, ExprNode)
    assert expr.op == "D"
    assert expr.args == ["x"]
    assert expr.wrt == "t"
    assert expr.dim is None

    expr_data_with_dim = {
        "op": "grad",
        "args": ["T"],
        "dim": "x"
    }
    expr = _parse_expression(expr_data_with_dim)
    assert expr.dim == "x"


def test_load_comprehensive_fields():
    """Test loading ESM file with events, data_loaders, operators, coupling, and solver."""
    comprehensive_esm = {
        "esm": "0.1.0",
        "metadata": {"name": "Comprehensive Test"},
        "models": {
            "test_model": {
                "variables": {"x": {"type": "state"}},
                "equations": [{"lhs": "x", "rhs": 1}],
                "discrete_events": [
                    {
                        "name": "reset_event",
                        "trigger": {"type": "periodic", "interval": 100},
                        "affects": [{"lhs": "x", "rhs": 0}]
                    }
                ],
                "continuous_events": [
                    {
                        "name": "threshold_event",
                        "conditions": [{"op": ">", "args": ["x", 10]}],
                        "affects": [{"lhs": "x", "rhs": 5}]
                    }
                ]
            }
        },
        "data_loaders": {
            "weather": {
                "type": "gridded_data",
                "loader_id": "ERA5",
                "provides": {
                    "temperature": {"units": "K", "description": "Air temperature"},
                    "pressure": {"units": "Pa", "description": "Air pressure"}
                }
            }
        },
        "operators": {
            "interpolator": {
                "operator_id": "linear_interp",
                "needed_vars": ["temperature"],
                "modifies": ["temp_interp"]
            }
        },
        "coupling": [
            {
                "type": "operator_compose",
                "systems": ["model1", "model2"],
                "description": "Compose two models"
            },
            {
                "type": "variable_map",
                "from": "weather.temperature",
                "to": "test_model.T",
                "transform": "param_to_var",
                "description": "Map temperature"
            }
        ],
        "solver": {
            "strategy": "strang_threads",
            "config": {
                "timestep": 60.0,
                "stiff_kwargs": {"abstol": 1e-8, "reltol": 1e-6}
            }
        }
    }

    json_str = json.dumps(comprehensive_esm)
    esm_file = load(json_str)

    # Verify all fields are parsed correctly (no longer empty!)
    assert len(esm_file.events) == 2
    assert len(esm_file.data_loaders) == 1
    assert len(esm_file.operators) == 1
    assert len(esm_file.couplings) == 2
    assert len(esm_file.solvers) == 1

    # Check events
    event_names = {event.name for event in esm_file.events}
    assert "reset_event" in event_names
    assert "threshold_event" in event_names

    # Check data loader
    data_loader = esm_file.data_loaders[0]
    assert data_loader.name == "weather"
    assert len(data_loader.variables) == 2
    assert "temperature" in data_loader.variables
    assert "pressure" in data_loader.variables

    # Check operator
    operator = esm_file.operators[0]
    assert operator.name == "interpolator"
    assert "temperature" in operator.input_variables
    assert "temp_interp" in operator.output_variables

    # Check couplings
    coupling_systems = [(c.source_model, c.target_model) for c in esm_file.couplings]
    assert ("model1", "model2") in coupling_systems

    # Check solver
    solver = esm_file.solvers[0]
    assert solver.algorithm == "strang_threads"
    assert "absolute" in solver.tolerances
    assert "relative" in solver.tolerances