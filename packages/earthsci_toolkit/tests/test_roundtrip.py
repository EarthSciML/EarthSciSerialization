"""Tests for round-trip functionality: load(save(load(json))) == load(json)."""

import json
from pathlib import Path

import pytest

from earthsci_toolkit import load, save
from earthsci_toolkit.esm_types import (
    EsmFile, Metadata, Model, ModelVariable, Equation, ExprNode,
    ReactionSystem, Species, Parameter, Reaction
)


def test_roundtrip_minimal():
    """Test round-trip with minimal ESM file."""
    original_json = {
        "esm": "0.1.0",
        "metadata": {
            "name": "Minimal Test"
        },
        "models": {
            "simple": {
                "variables": {
                    "x": {"type": "state"}
                },
                "equations": [
                    {"lhs": "x", "rhs": 1}
                ]
            }
        }
    }

    # Convert to JSON string
    json_str = json.dumps(original_json)

    # First load
    esm_file1 = load(json_str)

    # Save to JSON string
    json_str2 = save(esm_file1)

    # Second load
    esm_file2 = load(json_str2)

    # Third save (should be identical to second)
    json_str3 = save(esm_file2)

    # Compare the final two JSON strings - they should be identical
    data2 = json.loads(json_str2)
    data3 = json.loads(json_str3)

    assert data2 == data3


def test_roundtrip_reaction_system():
    """Test round-trip with reaction system."""
    original_json = {
        "esm": "0.1.0",
        "metadata": {
            "name": "Reaction Round-trip Test",
            "description": "Test reaction system round-trip"
        },
        "reaction_systems": {
            "simple_reaction": {
                "species": {
                    "A": {"units": "mol", "description": "Species A"},
                    "B": {"units": "mol", "description": "Species B"},
                    "C": {"units": "mol", "description": "Product C"}
                },
                "parameters": {
                    "k1": {"units": "1/(mol*s)", "default": 0.1, "description": "Rate constant"},
                    "k2": {"units": "1/s", "default": 0.05}
                },
                "reactions": [
                    {
                        "id": "R1",
                        "name": "Forward reaction",
                        "substrates": [
                            {"species": "A", "stoichiometry": 1},
                            {"species": "B", "stoichiometry": 1}
                        ],
                        "products": [
                            {"species": "C", "stoichiometry": 1}
                        ],
                        "rate": "k1"
                    },
                    {
                        "id": "R2",
                        "name": "Reverse reaction",
                        "substrates": [
                            {"species": "C", "stoichiometry": 1}
                        ],
                        "products": [
                            {"species": "A", "stoichiometry": 1},
                            {"species": "B", "stoichiometry": 1}
                        ],
                        "rate": "k2"
                    }
                ]
            }
        }
    }

    json_str = json.dumps(original_json)

    # First round-trip
    esm_file1 = load(json_str)
    json_str2 = save(esm_file1)
    esm_file2 = load(json_str2)
    json_str3 = save(esm_file2)

    # Compare final two JSON outputs
    data2 = json.loads(json_str2)
    data3 = json.loads(json_str3)

    assert data2 == data3

    # Verify specific components are preserved
    assert data2["esm"] == "0.1.0"
    assert data2["metadata"]["name"] == "Reaction Round-trip Test"
    assert "simple_reaction" in data2["reaction_systems"]

    rs_data = data2["reaction_systems"]["simple_reaction"]
    assert len(rs_data["species"]) == 3
    assert len(rs_data["parameters"]) == 2
    assert len(rs_data["reactions"]) == 2


def test_roundtrip_complex_expression():
    """Test round-trip with complex nested expressions."""
    original_json = {
        "esm": "0.1.0",
        "metadata": {
            "name": "Expression Test"
        },
        "models": {
            "complex_model": {
                "variables": {
                    "x": {"type": "state"},
                    "y": {"type": "state"},
                    "z": {"type": "observed", "expression": {
                        "op": "*",
                        "args": [
                            {
                                "op": "+",
                                "args": ["x", "y"]
                            },
                            2.5
                        ]
                    }}
                },
                "equations": [
                    {
                        "lhs": {
                            "op": "D",
                            "args": ["x"],
                            "wrt": "t"
                        },
                        "rhs": {
                            "op": "sin",
                            "args": ["y"]
                        }
                    },
                    {
                        "lhs": {
                            "op": "D",
                            "args": ["y"],
                            "wrt": "t"
                        },
                        "rhs": {
                            "op": "-",
                            "args": [
                                "x",
                                {
                                    "op": "^",
                                    "args": ["y", 2]
                                }
                            ]
                        }
                    }
                ]
            }
        }
    }

    json_str = json.dumps(original_json)

    # Double round-trip
    esm_file1 = load(json_str)
    json_str2 = save(esm_file1)
    esm_file2 = load(json_str2)
    json_str3 = save(esm_file2)

    # Parse final JSON
    data2 = json.loads(json_str2)
    data3 = json.loads(json_str3)

    assert data2 == data3

    # Check complex expressions are preserved
    model_data = data2["models"]["complex_model"]

    # Check observed variable expression
    z_expr = model_data["variables"]["z"]["expression"]
    assert z_expr["op"] == "*"
    assert z_expr["args"][1] == 2.5
    assert z_expr["args"][0]["op"] == "+"

    # Check equation expressions
    eq1_lhs = model_data["equations"][0]["lhs"]
    assert eq1_lhs["op"] == "D"
    assert eq1_lhs["wrt"] == "t"

    eq2_rhs = model_data["equations"][1]["rhs"]
    assert eq2_rhs["op"] == "-"
    assert eq2_rhs["args"][1]["op"] == "^"


def test_roundtrip_preserves_metadata():
    """Test that all metadata fields are preserved through round-trip."""
    original_json = {
        "esm": "0.1.0",
        "metadata": {
            "name": "Full Metadata Test",
            "description": "A test with all metadata fields",
            "authors": ["Alice Smith", "Bob Jones"],
            "created": "2024-01-01T00:00:00Z",
            "modified": "2024-01-02T00:00:00Z",
            "tags": ["test", "metadata", "validation"],
            "references": [
                {
                    "citation": "Smith et al. (2024)",
                    "doi": "10.1000/test.doi",
                    "url": "https://example.com/paper"
                }
            ]
        },
        "models": {
            "meta_model": {
                "variables": {
                    "x": {"type": "state"}
                },
                "equations": [
                    {"lhs": "x", "rhs": 0}
                ]
            }
        }
    }

    json_str = json.dumps(original_json)

    # Round-trip
    esm_file = load(json_str)
    json_str2 = save(esm_file)
    data = json.loads(json_str2)

    # Check all metadata is preserved
    metadata = data["metadata"]
    assert metadata["name"] == "Full Metadata Test"
    assert metadata["description"] == "A test with all metadata fields"
    assert metadata["authors"] == ["Alice Smith", "Bob Jones"]
    assert metadata["created"] == "2024-01-01T00:00:00Z"
    assert metadata["modified"] == "2024-01-02T00:00:00Z"
    assert metadata["tags"] == ["test", "metadata", "validation"]
    assert len(metadata["references"]) == 1

    ref = metadata["references"][0]
    assert ref["citation"] == "Smith et al. (2024)"
    assert ref["doi"] == "10.1000/test.doi"
    assert ref["url"] == "https://example.com/paper"


def test_roundtrip_index_outside_arrayop():
    """Round-trip for `index` op used in scalar RHS contexts (outside
    `arrayop.expr`), per RFC discretization §5.1. Exercises integer-literal
    and composite-arithmetic index arguments, plus a coexisting `index`
    inside an `arrayop.expr` body, to ensure both contexts survive
    load → save → load idempotently.
    """
    repo_root = Path(__file__).resolve().parents[3]
    fixture_path = repo_root / "tests" / "indexing" / "idx_outside_arrayop.esm"
    json_str = fixture_path.read_text()

    esm1 = load(json_str)
    json_str2 = save(esm1)
    esm2 = load(json_str2)
    json_str3 = save(esm2)

    # Idempotence: second save must equal third save under parsed JSON comparison.
    assert json.loads(json_str2) == json.loads(json_str3)

    # Semantic anchor: verify the `index` nodes survive on the right equations.
    data = json.loads(json_str3)
    eqs = data["models"]["IdxOutsideArrayop"]["equations"]
    assert len(eqs) == 3
    # Scalar ODE with integer-literal index: D(s_literal) = index(u, 2)
    assert eqs[1]["rhs"]["op"] == "index"
    assert eqs[1]["rhs"]["args"][0] == "u"
    assert eqs[1]["rhs"]["args"][1] == 2
    # Scalar ODE with composite index expression: index(u, 1+2)
    assert eqs[2]["rhs"]["op"] == "index"
    composite_idx = eqs[2]["rhs"]["args"][1]
    assert isinstance(composite_idx, dict)
    assert composite_idx["op"] == "+"


def test_roundtrip_preserves_int_float_distinction():
    """Integer and float literals must round-trip as distinct kinds.

    Per discretization RFC §5.4.1, an integer literal and a float literal
    are distinct AST nodes. Python natively preserves this through `int`
    vs `float` union members; this test pins the invariant.
    """
    original_json = {
        "esm": "0.1.0",
        "metadata": {"name": "int-float-distinction"},
        "models": {
            "m": {
                "variables": {
                    "x": {"type": "state"},
                    "y": {"type": "state"},
                },
                "equations": [
                    {"lhs": "x", "rhs": 1},        # integer literal
                    {"lhs": "y", "rhs": 1.0},      # float literal
                    {"lhs": "x", "rhs": {"op": "+", "args": [1, 2.5]}},
                    {"lhs": "y", "rhs": {"op": "+", "args": [1.0, 2.5]}},
                ],
            }
        },
    }

    json_str = json.dumps(original_json)
    esm_file = load(json_str)
    json_str2 = save(esm_file)
    data = json.loads(json_str2)

    eqs = data["models"]["m"]["equations"]

    # Integer literal survives as JSON integer (type(int), not type(float)).
    assert type(eqs[0]["rhs"]) is int
    assert eqs[0]["rhs"] == 1

    # Float literal survives as JSON float. `1.0` serializes as "1.0".
    assert type(eqs[1]["rhs"]) is float
    assert eqs[1]["rhs"] == 1.0
    assert "1.0" in json_str2  # ensures trailing .0 is emitted for integer-valued float

    # Inside an operator node: mixed int/float preserves each arg's kind.
    assert type(eqs[2]["rhs"]["args"][0]) is int
    assert type(eqs[2]["rhs"]["args"][1]) is float
    assert type(eqs[3]["rhs"]["args"][0]) is float
    assert type(eqs[3]["rhs"]["args"][1]) is float