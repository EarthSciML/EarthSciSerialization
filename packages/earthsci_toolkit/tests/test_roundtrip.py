"""Tests for round-trip functionality: load(save(load(json))) == load(json)."""

import json
import pytest

from esm_format import load, save
from esm_format.esm_types import (
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
                    "k1": {"units": "1/s", "default": 0.1, "description": "Rate constant"},
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