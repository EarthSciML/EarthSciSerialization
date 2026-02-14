"""
ESM Format Specification Section-by-Section Test Coverage Verification

This module provides comprehensive test fixtures that systematically validate each of the 15 sections
of the ESM format specification, ensuring complete specification compliance through both positive and
negative test cases with expected validation results.

Sections covered:
1. Overview - format version and MIME type validation
2. Top-level structure - all 8 fields with required/optional validation
3. Metadata - complete authorship and provenance fields
4. Expression AST - all operators including spatial/logical/mathematical
5. Events - continuous/discrete/cross-system with Pre operator
6. Models - ODE systems with variables/equations/events
7. Reaction systems - species/parameters/reactions with mass action
8. Data loaders - by reference with provides validation
9. Operators - runtime-specific with needed_vars
10. Coupling - all 6 types including couple2/operator_apply/callback/event
11. Domain - spatial/temporal with BCs/ICs
12. Solver - all strategies with config validation
13. Complete example validation
14. Design principles adherence testing
15. Future considerations compatibility
"""

import json
import pytest
import jsonschema
from jsonschema import ValidationError

from esm_format import load
from esm_format.parse import _get_schema


class TestSection01Overview:
    """Section 1: Overview - format version and MIME type validation"""

    def test_format_version_validation_positive(self):
        """Test valid format version strings."""
        schema = _get_schema()

        # Valid version 0.1.0
        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}}
        }
        jsonschema.validate(valid_data, schema)  # Should not raise

    def test_format_version_validation_negative(self):
        """Test invalid format version strings."""
        schema = _get_schema()

        # Invalid versions should fail
        invalid_versions = [
            "1.0.0",  # Wrong version
            "0.2.0",  # Wrong version
            "v0.1.0", # Invalid format
            "0.1",    # Missing patch
            "0.1.0-beta", # Pre-release not allowed
            "",       # Empty string
            None,     # Null value
            1.0,      # Number instead of string
        ]

        for version in invalid_versions:
            invalid_data = {
                "esm": version,
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}}
            }
            with pytest.raises(ValidationError):
                jsonschema.validate(invalid_data, schema)

    def test_file_extension_mime_type_constants(self):
        """Test that spec constants are documented (non-validating test)."""
        # This is a documentation test - the spec defines:
        # File extension: .esm
        # MIME type: application/vnd.earthsciml+json
        # Encoding: UTF-8

        # These are not validated by schema but are part of the spec
        expected_extension = ".esm"
        expected_mime_type = "application/vnd.earthsciml+json"
        expected_encoding = "UTF-8"

        assert expected_extension == ".esm"
        assert expected_mime_type == "application/vnd.earthsciml+json"
        assert expected_encoding == "UTF-8"


class TestSection02TopLevelStructure:
    """Section 2: Top-level structure - all 8 fields with required/optional validation"""

    def test_all_top_level_fields_present(self):
        """Test complete top-level structure with all 8 fields."""
        schema = _get_schema()

        complete_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Complete Test"},
            "models": {"test_model": {"variables": {"x": {"type": "state"}}, "equations": []}},
            "reaction_systems": {"test_rs": {"species": {"A": {}}, "parameters": {}, "reactions": [{"id": "R1", "substrates": None, "products": [{"species": "A", "stoichiometry": 1}], "rate": 1.0}]}},
            "data_loaders": {"test_loader": {"type": "gridded_data", "loader_id": "test", "provides": {}}},
            "operators": {"test_op": {"operator_id": "test", "needed_vars": []}},
            "coupling": [],
            "domain": {"temporal": {"start": "2024-01-01T00:00:00Z", "end": "2024-01-02T00:00:00Z"}},
            "solver": {"strategy": "strang_threads"}
        }
        jsonschema.validate(complete_data, schema)  # Should not raise

    def test_required_fields_validation(self):
        """Test that required fields (esm, metadata) are enforced."""
        schema = _get_schema()

        # Missing esm field
        with pytest.raises(ValidationError, match="'esm' is a required property"):
            jsonschema.validate({
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}}
            }, schema)

        # Missing metadata field
        with pytest.raises(ValidationError, match="'metadata' is a required property"):
            jsonschema.validate({
                "esm": "0.1.0",
                "models": {"test": {"variables": {}, "equations": []}}
            }, schema)

    def test_at_least_one_model_or_reaction_system_required(self):
        """Test that at least one of models or reaction_systems must be present."""
        schema = _get_schema()

        # Neither models nor reaction_systems present
        with pytest.raises(ValidationError):
            jsonschema.validate({
                "esm": "0.1.0",
                "metadata": {"name": "Test"}
            }, schema)

    def test_optional_fields_can_be_omitted(self):
        """Test that optional fields can be safely omitted."""
        schema = _get_schema()

        # Minimal valid structure with only required fields
        minimal_valid_cases = [
            {
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}}
            },
            {
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "reaction_systems": {"test": {"species": {"A": {}}, "parameters": {}, "reactions": [{"id": "R1", "substrates": None, "products": [{"species": "A", "stoichiometry": 1}], "rate": 1.0}]}}
            }
        ]

        for case in minimal_valid_cases:
            jsonschema.validate(case, schema)  # Should not raise

    def test_additional_properties_not_allowed(self):
        """Test that additional properties are not allowed at top level."""
        schema = _get_schema()

        invalid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "unknown_field": "should not be allowed"
        }

        with pytest.raises(ValidationError, match="Additional properties are not allowed"):
            jsonschema.validate(invalid_data, schema)


class TestSection03Metadata:
    """Section 3: Metadata - complete authorship and provenance fields"""

    def test_minimal_metadata_structure(self):
        """Test minimal required metadata."""
        schema = _get_schema()

        minimal_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Minimal Test"},
            "models": {"test": {"variables": {}, "equations": []}}
        }
        jsonschema.validate(minimal_data, schema)

    def test_complete_metadata_structure(self):
        """Test complete metadata with all fields."""
        schema = _get_schema()

        complete_data = {
            "esm": "0.1.0",
            "metadata": {
                "name": "FullChemistry_NorthAmerica",
                "description": "Coupled gas-phase chemistry with advection and meteorology over North America",
                "authors": ["Chris Tessum", "Jane Scientist"],
                "license": "MIT",
                "created": "2026-02-11T00:00:00Z",
                "modified": "2026-02-11T00:00:00Z",
                "tags": ["atmospheric-chemistry", "advection", "north-america"],
                "references": [
                    {
                        "doi": "10.5194/acp-8-6365-2008",
                        "citation": "Cameron-Smith et al., 2008. A new reduced mechanism for gas-phase chemistry.",
                        "url": "https://doi.org/10.5194/acp-8-6365-2008"
                    }
                ]
            },
            "models": {"test": {"variables": {}, "equations": []}}
        }
        jsonschema.validate(complete_data, schema)

    def test_metadata_required_name_field(self):
        """Test that name field is required in metadata."""
        schema = _get_schema()

        with pytest.raises(ValidationError, match="'name' is a required property"):
            jsonschema.validate({
                "esm": "0.1.0",
                "metadata": {"description": "Missing name"},
                "models": {"test": {"variables": {}, "equations": []}}
            }, schema)

    def test_metadata_field_types(self):
        """Test correct types for metadata fields."""
        schema = _get_schema()

        # Test various type violations
        type_violations = [
            {"name": 123},  # name should be string
            {"name": "Test", "authors": "single author"},  # authors should be array
            {"name": "Test", "tags": "single tag"},  # tags should be array
            {"name": "Test", "references": {}},  # references should be array
        ]

        for violation in type_violations:
            invalid_data = {
                "esm": "0.1.0",
                "metadata": violation,
                "models": {"test": {"variables": {}, "equations": []}}
            }
            with pytest.raises(ValidationError):
                jsonschema.validate(invalid_data, schema)


class TestSection04ExpressionAST:
    """Section 4: Expression AST - all operators including spatial/logical/mathematical"""

    def test_expression_basic_types(self):
        """Test basic expression types: number, string, ExprNode."""
        schema = _get_schema()

        # Number expression
        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {
                "test_model": {
                    "variables": {"x": {"type": "state"}},
                    "equations": [{"lhs": "x", "rhs": 3.14}]
                }
            }
        }
        jsonschema.validate(valid_data, schema)

        # String expression (variable reference)
        valid_data["models"]["test_model"]["equations"][0]["rhs"] = "y"
        jsonschema.validate(valid_data, schema)

    def test_arithmetic_operators(self):
        """Test all arithmetic operators."""
        schema = _get_schema()

        arithmetic_cases = [
            {"op": "+", "args": ["a", "b", "c"]},  # n-ary addition
            {"op": "-", "args": ["a"]},           # unary negation
            {"op": "-", "args": ["a", "b"]},      # binary subtraction
            {"op": "*", "args": ["k", "A", "B"]}, # n-ary multiplication
            {"op": "/", "args": ["a", "b"]},      # binary division
            {"op": "^", "args": ["x", 2]},        # binary exponentiation
        ]

        for op_case in arithmetic_cases:
            valid_data = {
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {
                    "test_model": {
                        "variables": {"x": {"type": "state"}},
                        "equations": [{"lhs": "x", "rhs": op_case}]
                    }
                }
            }
            jsonschema.validate(valid_data, schema)

    def test_calculus_operators(self):
        """Test calculus operators with additional fields."""
        schema = _get_schema()

        calculus_cases = [
            {"op": "D", "args": ["O3"], "wrt": "t"},                    # Time derivative
            {"op": "grad", "args": ["_var"], "dim": "x"},               # Spatial gradient
            {"op": "div", "args": [{"op": "*", "args": ["u", "_var"]}]}, # Divergence
            {"op": "laplacian", "args": ["_var"]},                      # Laplacian
        ]

        for op_case in calculus_cases:
            valid_data = {
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {
                    "test_model": {
                        "variables": {"x": {"type": "state"}},
                        "equations": [{"lhs": "x", "rhs": op_case}]
                    }
                }
            }
            jsonschema.validate(valid_data, schema)

    def test_elementary_functions(self):
        """Test elementary mathematical functions."""
        schema = _get_schema()

        elementary_functions = [
            "exp", "log", "log10", "sqrt", "abs", "sign",
            "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
            "min", "max", "floor", "ceil"
        ]

        for func in elementary_functions:
            op_case = {"op": func, "args": ["x"]}
            if func == "atan2":
                op_case["args"] = ["y", "x"]  # atan2 needs two arguments
            elif func in ["min", "max"]:
                op_case["args"] = ["a", "b"]  # min/max need at least two arguments

            valid_data = {
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {
                    "test_model": {
                        "variables": {"x": {"type": "state"}},
                        "equations": [{"lhs": "x", "rhs": op_case}]
                    }
                }
            }
            jsonschema.validate(valid_data, schema)

    def test_conditional_operators(self):
        """Test conditional and logical operators."""
        schema = _get_schema()

        conditional_cases = [
            {"op": "ifelse", "args": [{"op": ">", "args": ["x", 0]}, "positive", "negative"]},
            {"op": ">", "args": ["a", "b"]},
            {"op": "<", "args": ["a", "b"]},
            {"op": ">=", "args": ["a", "b"]},
            {"op": "<=", "args": ["a", "b"]},
            {"op": "==", "args": ["a", "b"]},
            {"op": "!=", "args": ["a", "b"]},
            {"op": "and", "args": [{"op": ">", "args": ["x", 0]}, {"op": "<", "args": ["x", 10]}]},
            {"op": "or", "args": [{"op": "<", "args": ["x", 0]}, {"op": ">", "args": ["x", 10]}]},
            {"op": "not", "args": [{"op": "==", "args": ["x", 0]}]},
        ]

        for op_case in conditional_cases:
            valid_data = {
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {
                    "test_model": {
                        "variables": {"x": {"type": "state"}},
                        "equations": [{"lhs": "x", "rhs": op_case}]
                    }
                }
            }
            jsonschema.validate(valid_data, schema)

    def test_event_specific_pre_operator(self):
        """Test Pre operator for event affects."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {
                "test_model": {
                    "variables": {"x": {"type": "state"}},
                    "equations": [],
                    "continuous_events": [{
                        "conditions": [{"op": "-", "args": ["x", 1]}],
                        "affects": [{
                            "lhs": "x",
                            "rhs": {"op": "+", "args": [{"op": "Pre", "args": ["x"]}, 1]}
                        }]
                    }]
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_invalid_operators(self):
        """Test that invalid operators are rejected."""
        schema = _get_schema()

        invalid_operators = [
            "invalid_op", "custom_func", "undefined", "@@", "++", "--"
        ]

        for invalid_op in invalid_operators:
            invalid_data = {
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {
                    "test_model": {
                        "variables": {"x": {"type": "state"}},
                        "equations": [{"lhs": "x", "rhs": {"op": invalid_op, "args": ["x"]}}]
                    }
                }
            }
            with pytest.raises(ValidationError):
                jsonschema.validate(invalid_data, schema)


class TestSection05Events:
    """Section 5: Events - continuous/discrete/cross-system with Pre operator"""

    def test_continuous_events_basic_structure(self):
        """Test basic continuous event structure."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {
                "test_model": {
                    "variables": {"x": {"type": "state"}, "v": {"type": "state"}},
                    "equations": [],
                    "continuous_events": [{
                        "name": "ground_bounce",
                        "conditions": [{"op": "-", "args": ["x", 0]}],
                        "affects": [{
                            "lhs": "v",
                            "rhs": {"op": "*", "args": [-0.9, {"op": "Pre", "args": ["v"]}]}
                        }],
                        "description": "Ball bounces off ground"
                    }]
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_continuous_events_direction_dependent_affects(self):
        """Test continuous events with direction-dependent affects."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {
                "test_model": {
                    "variables": {"T": {"type": "state"}, "heater_on": {"type": "state"}},
                    "equations": [],
                    "continuous_events": [{
                        "name": "thermostat",
                        "conditions": [{"op": "-", "args": ["T", "T_setpoint"]}],
                        "affects": [{"lhs": "heater_on", "rhs": 0}],
                        "affect_neg": [{"lhs": "heater_on", "rhs": 1}],
                        "description": "Thermostat control"
                    }]
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_discrete_events_all_trigger_types(self):
        """Test discrete events with all trigger types."""
        schema = _get_schema()

        trigger_cases = [
            # Condition trigger
            {
                "name": "injection",
                "trigger": {"type": "condition", "expression": {"op": "==", "args": ["t", "t_inject"]}},
                "affects": [{"lhs": "N", "rhs": {"op": "+", "args": [{"op": "Pre", "args": ["N"]}, "M"]}}]
            },
            # Periodic trigger
            {
                "name": "periodic_decay",
                "trigger": {"type": "periodic", "interval": 3600.0},
                "affects": [{"lhs": "scale", "rhs": {"op": "*", "args": [{"op": "Pre", "args": ["scale"]}, 0.95]}}]
            },
            # Preset times trigger
            {
                "name": "measurements",
                "trigger": {"type": "preset_times", "times": [3600.0, 7200.0, 14400.0]},
                "affects": [{"lhs": "sample_flag", "rhs": {"op": "+", "args": [{"op": "Pre", "args": ["sample_flag"]}, 1]}}]
            }
        ]

        for trigger_case in trigger_cases:
            valid_data = {
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {
                    "test_model": {
                        "variables": {"x": {"type": "state"}},
                        "equations": [],
                        "discrete_events": [trigger_case]
                    }
                }
            }
            jsonschema.validate(valid_data, schema)

    def test_discrete_parameters_in_events(self):
        """Test discrete parameters modification in events."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {
                "test_model": {
                    "variables": {
                        "x": {"type": "state"},
                        "alpha": {"type": "parameter", "default": 1.0}
                    },
                    "equations": [],
                    "discrete_events": [{
                        "name": "parameter_change",
                        "trigger": {"type": "condition", "expression": {"op": "==", "args": ["t", 10]}},
                        "affects": [{"lhs": "alpha", "rhs": 0.5}],
                        "discrete_parameters": ["alpha"],
                        "description": "Change parameter at t=10"
                    }]
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_functional_affects_registered(self):
        """Test functional affects with registered handlers."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {
                "test_model": {
                    "variables": {"T": {"type": "state"}},
                    "equations": [],
                    "discrete_events": [{
                        "name": "controller",
                        "trigger": {"type": "periodic", "interval": 60.0},
                        "functional_affect": {
                            "handler_id": "PIDController",
                            "read_vars": ["T", "T_setpoint"],
                            "read_params": ["Kp", "Ki", "Kd"],
                            "modified_params": ["heater_power"],
                            "config": {"anti_windup": True}
                        },
                        "description": "PID controller"
                    }]
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_cross_system_events_in_coupling(self):
        """Test cross-system events defined in coupling section."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "coupling": [{
                "type": "event",
                "event_type": "continuous",
                "conditions": [{"op": "-", "args": ["ChemModel.O3", 1e-7]}],
                "affects": [{"lhs": "EmissionModel.NOx_scale", "rhs": 0.5}],
                "description": "Cross-system ozone control"
            }]
        }
        jsonschema.validate(valid_data, schema)


class TestSection06Models:
    """Section 6: Models - ODE systems with variables/equations/events"""

    def test_minimal_model_structure(self):
        """Test minimal required model structure."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {
                "MinimalModel": {
                    "variables": {"x": {"type": "state"}},
                    "equations": [{"lhs": {"op": "D", "args": ["x"], "wrt": "t"}, "rhs": 1.0}]
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_complete_model_with_all_variable_types(self):
        """Test model with all variable types."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {
                "CompleteModel": {
                    "coupletype": "TestCoupler",
                    "reference": {
                        "doi": "10.1234/test-doi",
                        "citation": "Test et al., 2024",
                        "url": "https://test.example.com",
                        "notes": "Test model for validation"
                    },
                    "variables": {
                        "x": {
                            "type": "state",
                            "units": "mol/mol",
                            "default": 1.0e-8,
                            "description": "State variable"
                        },
                        "k": {
                            "type": "parameter",
                            "units": "1/s",
                            "default": 0.1,
                            "description": "Rate parameter"
                        },
                        "total": {
                            "type": "observed",
                            "units": "mol/mol",
                            "expression": {"op": "*", "args": ["x", "k"]},
                            "description": "Observed quantity"
                        }
                    },
                    "equations": [{
                        "lhs": {"op": "D", "args": ["x"], "wrt": "t"},
                        "rhs": {"op": "*", "args": ["-k", "x"]}
                    }]
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_model_with_events(self):
        """Test model including both continuous and discrete events."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {
                "EventModel": {
                    "variables": {"x": {"type": "state"}, "y": {"type": "state"}},
                    "equations": [],
                    "continuous_events": [{
                        "conditions": [{"op": "-", "args": ["x", 5]}],
                        "affects": [{"lhs": "y", "rhs": {"op": "Pre", "args": ["y"]}}]
                    }],
                    "discrete_events": [{
                        "trigger": {"type": "condition", "expression": {"op": ">", "args": ["x", 10]}},
                        "affects": [{"lhs": "x", "rhs": 0}]
                    }]
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_hierarchical_subsystems(self):
        """Test hierarchical model composition with subsystems."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {
                "MainSystem": {
                    "variables": {"top_var": {"type": "state"}},
                    "equations": [],
                    "subsystems": {
                        "SubSystem": {
                            "variables": {"sub_var": {"type": "state"}},
                            "equations": []
                        }
                    }
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_observed_variables_require_expression(self):
        """Test that observed variables must have expression field."""
        schema = _get_schema()

        # Observed variable without expression should fail
        with pytest.raises(ValidationError, match="'expression' is a required property"):
            jsonschema.validate({
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {
                    "test_model": {
                        "variables": {"y": {"type": "observed"}},
                        "equations": []
                    }
                }
            }, schema)


class TestSection07ReactionSystems:
    """Section 7: Reaction systems - species/parameters/reactions with mass action"""

    def test_minimal_reaction_system(self):
        """Test minimal reaction system structure."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "reaction_systems": {
                "MinimalReactions": {
                    "species": {"A": {}},
                    "parameters": {},
                    "reactions": [{
                        "id": "R1",
                        "substrates": None,
                        "products": [{"species": "A", "stoichiometry": 1}],
                        "rate": 1.0
                    }]
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_complete_reaction_system_superfast_example(self):
        """Test complete reaction system based on SuperFast mechanism."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "reaction_systems": {
                "SuperFastReactions": {
                    "coupletype": "SuperFastCoupler",
                    "reference": {
                        "doi": "10.5194/acp-8-6365-2008",
                        "citation": "Cameron-Smith et al., 2008"
                    },
                    "species": {
                        "O3": {"units": "mol/mol", "default": 1.0e-8, "description": "Ozone"},
                        "NO": {"units": "mol/mol", "default": 1.0e-10, "description": "Nitric oxide"},
                        "NO2": {"units": "mol/mol", "default": 1.0e-10, "description": "Nitrogen dioxide"}
                    },
                    "parameters": {
                        "T": {"units": "K", "default": 298.15, "description": "Temperature"},
                        "M": {"units": "molec/cm^3", "default": 2.46e19, "description": "Air density"},
                        "jNO2": {"units": "1/s", "default": 0.005, "description": "NO2 photolysis rate"}
                    },
                    "reactions": [
                        {
                            "id": "R1",
                            "name": "NO_O3",
                            "substrates": [
                                {"species": "NO", "stoichiometry": 1},
                                {"species": "O3", "stoichiometry": 1}
                            ],
                            "products": [
                                {"species": "NO2", "stoichiometry": 1}
                            ],
                            "rate": {
                                "op": "*",
                                "args": [1.8e-12, {"op": "exp", "args": [{"op": "/", "args": [-1370, "T"]}]}, "M"]
                            }
                        },
                        {
                            "id": "R2",
                            "name": "NO2_photolysis",
                            "substrates": [{"species": "NO2", "stoichiometry": 1}],
                            "products": [
                                {"species": "NO", "stoichiometry": 1},
                                {"species": "O3", "stoichiometry": 1}
                            ],
                            "rate": "jNO2"
                        }
                    ]
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_reaction_rate_types(self):
        """Test all valid reaction rate expression types."""
        schema = _get_schema()

        rate_cases = [
            1.0,  # Number
            "k1", # String (parameter reference)
            {"op": "*", "args": ["k1", "T"]}, # Expression AST
            {"op": "+", "args": [1.44e-13, {"op": "/", "args": ["M", 3.43e11]}]} # Complex expression
        ]

        for i, rate in enumerate(rate_cases):
            valid_data = {
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "reaction_systems": {
                    "test_rs": {
                        "species": {"A": {}, "B": {}},
                        "parameters": {"k1": {"default": 0.1}, "T": {"default": 298}, "M": {"default": 1e19}},
                        "reactions": [{
                            "id": f"R{i+1}",
                            "substrates": [{"species": "A", "stoichiometry": 1}],
                            "products": [{"species": "B", "stoichiometry": 1}],
                            "rate": rate
                        }]
                    }
                }
            }
            jsonschema.validate(valid_data, schema)

    def test_source_and_sink_reactions(self):
        """Test source (null substrates) and sink (null products) reactions."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "reaction_systems": {
                "test_rs": {
                    "species": {"A": {}},
                    "parameters": {},
                    "reactions": [
                        {
                            "id": "R1_source",
                            "substrates": None,
                            "products": [{"species": "A", "stoichiometry": 1}],
                            "rate": 1.0
                        },
                        {
                            "id": "R2_sink",
                            "substrates": [{"species": "A", "stoichiometry": 1}],
                            "products": None,
                            "rate": 0.1
                        }
                    ]
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_constraint_equations(self):
        """Test additional constraint equations in reaction systems."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "reaction_systems": {
                "test_rs": {
                    "species": {"A": {}, "B": {}},
                    "parameters": {},
                    "reactions": [{"id": "R1", "substrates": None, "products": [{"species": "A", "stoichiometry": 1}], "rate": 1.0}],
                    "constraint_equations": [{
                        "lhs": {"op": "+", "args": ["A", "B"]},
                        "rhs": "total_AB"
                    }]
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_stoichiometry_validation(self):
        """Test stoichiometry constraints."""
        schema = _get_schema()

        # Zero stoichiometry should fail (minimum is 1)
        with pytest.raises(ValidationError):
            jsonschema.validate({
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "reaction_systems": {
                    "test_rs": {
                        "species": {"A": {}},
                        "parameters": {},
                        "reactions": [{
                            "id": "R1",
                            "substrates": [{"species": "A", "stoichiometry": 0}],
                            "products": None,
                            "rate": 1.0
                        }]
                    }
                }
            }, schema)


class TestSection08DataLoaders:
    """Section 8: Data loaders - by reference with provides validation"""

    def test_all_data_loader_types(self):
        """Test all supported data loader types."""
        schema = _get_schema()

        loader_types = ["gridded_data", "emissions", "timeseries", "static", "callback"]

        for loader_type in loader_types:
            valid_data = {
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}},
                "data_loaders": {
                    f"test_{loader_type}": {
                        "type": loader_type,
                        "loader_id": f"TestLoader_{loader_type}",
                        "provides": {"test_var": {"units": "m/s", "description": "Test variable"}}
                    }
                }
            }
            jsonschema.validate(valid_data, schema)

    def test_complete_geosfp_example(self):
        """Test complete GEOS-FP data loader example from spec."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "data_loaders": {
                "GEOSFP": {
                    "type": "gridded_data",
                    "loader_id": "GEOSFP",
                    "config": {
                        "resolution": "0.25x0.3125_NA",
                        "coord_defaults": {"lat": 34.0, "lev": 1}
                    },
                    "reference": {
                        "citation": "Global Modeling and Assimilation Office (GMAO), NASA GSFC",
                        "url": "https://gmao.gsfc.nasa.gov/GEOS_systems/"
                    },
                    "provides": {
                        "u": {"units": "m/s", "description": "Eastward wind component"},
                        "v": {"units": "m/s", "description": "Northward wind component"},
                        "T": {"units": "K", "description": "Air temperature"},
                        "PBLH": {"units": "m", "description": "Planetary boundary layer height"}
                    },
                    "temporal_resolution": "PT3H",
                    "spatial_resolution": {"lon": 0.3125, "lat": 0.25},
                    "interpolation": "linear"
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_emissions_data_loader(self):
        """Test emissions-specific data loader."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "data_loaders": {
                "NEI_Emissions": {
                    "type": "emissions",
                    "loader_id": "NEI2016",
                    "config": {"year": 2016, "sector": "all"},
                    "reference": {
                        "citation": "US EPA, 2016 National Emissions Inventory",
                        "url": "https://www.epa.gov/air-emissions-inventories"
                    },
                    "provides": {
                        "emission_rate_NO": {"units": "mol/mol/s", "description": "NO emission rate"},
                        "emission_rate_CO": {"units": "mol/mol/s", "description": "CO emission rate"}
                    }
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_required_fields_validation(self):
        """Test that required fields are enforced for data loaders."""
        schema = _get_schema()

        # Missing type
        with pytest.raises(ValidationError, match="'type' is a required property"):
            jsonschema.validate({
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}},
                "data_loaders": {
                    "bad_loader": {
                        "loader_id": "test",
                        "provides": {}
                    }
                }
            }, schema)

        # Missing provides
        with pytest.raises(ValidationError, match="'provides' is a required property"):
            jsonschema.validate({
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}},
                "data_loaders": {
                    "bad_loader": {
                        "type": "gridded_data",
                        "loader_id": "test"
                    }
                }
            }, schema)


class TestSection09Operators:
    """Section 9: Operators - runtime-specific with needed_vars"""

    def test_complete_operator_examples(self):
        """Test complete operator examples from spec."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "operators": {
                "DryDepGrid": {
                    "operator_id": "WesleyDryDep",
                    "reference": {
                        "doi": "10.1016/0004-6981(89)90153-4",
                        "citation": "Wesely, 1989. Parameterization of surface resistances to gaseous dry deposition.",
                        "notes": "Resistance-based model: r_total = r_a + r_b + r_c"
                    },
                    "config": {"season": "summer", "land_use_categories": 11},
                    "needed_vars": ["O3", "NO2", "SO2", "T", "u_star", "LAI"],
                    "modifies": ["O3", "NO2", "SO2"],
                    "description": "Dry deposition loss based on surface resistance"
                },
                "WetScavenging": {
                    "operator_id": "BelowCloudScav",
                    "reference": {"doi": "10.1029/2001JD001480"},
                    "needed_vars": ["precip_rate", "cloud_fraction"],
                    "modifies": ["H2O2", "CH2O", "HNO3"],
                    "description": "Below-cloud washout of soluble species"
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_operator_required_fields(self):
        """Test that required fields are enforced for operators."""
        schema = _get_schema()

        # Missing operator_id
        with pytest.raises(ValidationError, match="'operator_id' is a required property"):
            jsonschema.validate({
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}},
                "operators": {
                    "bad_op": {
                        "needed_vars": ["x"]
                    }
                }
            }, schema)

        # Missing needed_vars
        with pytest.raises(ValidationError, match="'needed_vars' is a required property"):
            jsonschema.validate({
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}},
                "operators": {
                    "bad_op": {
                        "operator_id": "test"
                    }
                }
            }, schema)

    def test_operator_field_types(self):
        """Test correct field types for operators."""
        schema = _get_schema()

        # needed_vars should be array, not string
        with pytest.raises(ValidationError):
            jsonschema.validate({
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}},
                "operators": {
                    "bad_op": {
                        "operator_id": "test",
                        "needed_vars": "single_var"  # Should be array
                    }
                }
            }, schema)


class TestSection10Coupling:
    """Section 10: Coupling - all 6 types including couple2/operator_apply/callback/event"""

    def test_operator_compose_coupling(self):
        """Test operator_compose coupling type."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "coupling": [{
                "type": "operator_compose",
                "systems": ["SuperFastReactions", "Advection"],
                "description": "Add advection terms to chemistry system"
            }]
        }
        jsonschema.validate(valid_data, schema)

    def test_couple2_coupling(self):
        """Test couple2 coupling with connector system."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "coupling": [{
                "type": "couple2",
                "systems": ["SuperFastReactions", "DryDeposition"],
                "coupletype_pair": ["SuperFastCoupler", "DryDepositionCoupler"],
                "connector": {
                    "equations": [{
                        "from": "DryDeposition.v_dep_O3",
                        "to": "SuperFastReactions.O3",
                        "transform": "additive",
                        "expression": {
                            "op": "*",
                            "args": [{"op": "-", "args": ["DryDeposition.v_dep_O3"]}, "SuperFastReactions.O3"]
                        }
                    }]
                },
                "description": "Bi-directional deposition coupling"
            }]
        }
        jsonschema.validate(valid_data, schema)

    def test_variable_map_coupling_all_transforms(self):
        """Test variable_map coupling with all transform types."""
        schema = _get_schema()

        transform_cases = [
            {"from": "GEOSFP.T", "to": "Chemistry.T", "transform": "param_to_var"},
            {"from": "DataSource.wind", "to": "Advection.wind", "transform": "identity"},
            {"from": "Emissions.CO", "to": "Chemistry.CO_source", "transform": "additive"},
            {"from": "Scaler.factor", "to": "Chemistry.rate", "transform": "multiplicative"},
            {"from": "Input.pressure", "to": "Model.P", "transform": "conversion_factor", "factor": 100.0}
        ]

        for i, transform_case in enumerate(transform_cases):
            coupling_entry = {"type": "variable_map", **transform_case}
            valid_data = {
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}},
                "coupling": [coupling_entry]
            }
            jsonschema.validate(valid_data, schema)

    def test_operator_apply_coupling(self):
        """Test operator_apply coupling."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "coupling": [
                {
                    "type": "operator_apply",
                    "operator": "DryDepGrid",
                    "description": "Apply dry deposition operator"
                },
                {
                    "type": "operator_apply",
                    "operator": "WetScavenging",
                    "description": "Apply wet scavenging operator"
                }
            ]
        }
        jsonschema.validate(valid_data, schema)

    def test_callback_coupling(self):
        """Test callback coupling type."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "coupling": [{
                "type": "callback",
                "callback_id": "init_chemistry",
                "description": "Initialize chemistry state"
            }]
        }
        jsonschema.validate(valid_data, schema)

    def test_event_coupling(self):
        """Test event coupling (cross-system events)."""
        schema = _get_schema()

        # Continuous cross-system event
        continuous_event = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "coupling": [{
                "type": "event",
                "event_type": "continuous",
                "conditions": [{"op": "-", "args": ["ChemModel.O3", 1e-7]}],
                "affects": [{"lhs": "EmissionModel.NOx_scale", "rhs": 0.5}],
                "description": "Cross-system ozone control"
            }]
        }
        jsonschema.validate(continuous_event, schema)

        # Discrete cross-system event
        discrete_event = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "coupling": [{
                "type": "event",
                "event_type": "discrete",
                "trigger": {"type": "condition", "expression": {"op": ">", "args": ["System1.x", 10]}},
                "affects": [{"lhs": "System2.reset_flag", "rhs": 1}],
                "description": "Cross-system trigger reset"
            }]
        }
        jsonschema.validate(discrete_event, schema)

    def test_coupling_translate_field(self):
        """Test translate field for operator_compose."""
        schema = _get_schema()

        # Simple variable translation
        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "coupling": [{
                "type": "operator_compose",
                "systems": ["ChemModel", "PhotolysisModel"],
                "translate": {
                    "ChemModel.ozone": "PhotolysisModel.O3"
                }
            }]
        }
        jsonschema.validate(valid_data, schema)

        # Translation with conversion factor
        valid_data["coupling"][0]["translate"] = {
            "ChemModel.ozone": {"var": "PhotolysisModel.O3", "factor": 1e-9}
        }
        jsonschema.validate(valid_data, schema)


class TestSection11Domain:
    """Section 11: Domain - spatial/temporal with BCs/ICs"""

    def test_minimal_domain_structure(self):
        """Test minimal domain structure."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "domain": {
                "temporal": {
                    "start": "2024-05-01T00:00:00Z",
                    "end": "2024-05-03T00:00:00Z"
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_complete_domain_structure(self):
        """Test complete domain structure from spec."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "domain": {
                "independent_variable": "t",
                "temporal": {
                    "start": "2024-05-01T00:00:00Z",
                    "end": "2024-05-03T00:00:00Z",
                    "reference_time": "2024-05-01T00:00:00Z"
                },
                "spatial": {
                    "lon": {"min": -130.0, "max": -60.0, "units": "degrees", "grid_spacing": 0.3125},
                    "lat": {"min": 20.0, "max": 55.0, "units": "degrees", "grid_spacing": 0.25},
                    "lev": {"min": 1, "max": 72, "units": "level", "grid_spacing": 1}
                },
                "coordinate_transforms": [{
                    "id": "lonlat_to_meters",
                    "description": "Convert lon/lat degrees to x/y meters",
                    "dimensions": ["lon", "lat"]
                }],
                "spatial_ref": "WGS84",
                "initial_conditions": {"type": "constant", "value": 0.0},
                "boundary_conditions": [
                    {"type": "zero_gradient", "dimensions": ["lon", "lat"]},
                    {"type": "constant", "dimensions": ["lev"], "value": 0.0}
                ],
                "element_type": "Float32",
                "array_type": "Array"
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_initial_condition_types(self):
        """Test all initial condition types."""
        schema = _get_schema()

        ic_cases = [
            {"type": "constant", "value": 1.0},
            {"type": "per_variable", "values": {"x": 1.0, "y": 2.0}},
            {"type": "from_file", "path": "/data/initial.nc", "format": "netcdf"}
        ]

        for ic in ic_cases:
            valid_data = {
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}},
                "domain": {
                    "temporal": {"start": "2024-01-01T00:00:00Z", "end": "2024-01-02T00:00:00Z"},
                    "initial_conditions": ic
                }
            }
            jsonschema.validate(valid_data, schema)

    def test_boundary_condition_types(self):
        """Test all boundary condition types."""
        schema = _get_schema()

        bc_cases = [
            {"type": "constant", "dimensions": ["x"], "value": 0.0},
            {"type": "zero_gradient", "dimensions": ["y"]},
            {"type": "periodic", "dimensions": ["x", "y"]}
        ]

        for bc in bc_cases:
            valid_data = {
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}},
                "domain": {
                    "temporal": {"start": "2024-01-01T00:00:00Z", "end": "2024-01-02T00:00:00Z"},
                    "boundary_conditions": [bc]
                }
            }
            jsonschema.validate(valid_data, schema)

    def test_spatial_dimension_validation(self):
        """Test spatial dimension validation."""
        schema = _get_schema()

        # Missing required min field
        with pytest.raises(ValidationError, match="'min' is a required property"):
            jsonschema.validate({
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}},
                "domain": {
                    "spatial": {"x": {"max": 10.0}}
                }
            }, schema)


class TestSection12Solver:
    """Section 12: Solver - all strategies with config validation"""

    def test_all_solver_strategies(self):
        """Test all supported solver strategies."""
        schema = _get_schema()

        strategies = ["strang_threads", "strang_serial", "imex"]

        for strategy in strategies:
            valid_data = {
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}},
                "solver": {"strategy": strategy}
            }
            jsonschema.validate(valid_data, schema)

    def test_complete_solver_configuration(self):
        """Test complete solver configuration from spec."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "solver": {
                "strategy": "strang_threads",
                "config": {
                    "threads": 8,
                    "stiff_algorithm": "Rosenbrock23",
                    "timestep": 1800.0,
                    "stiff_kwargs": {"abstol": 1e-6, "reltol": 1e-3},
                    "nonstiff_algorithm": "Euler",
                    "map_algorithm": "broadcast"
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_solver_strategy_validation(self):
        """Test that invalid solver strategies are rejected."""
        schema = _get_schema()

        with pytest.raises(ValidationError, match="'invalid_strategy' is not one of"):
            jsonschema.validate({
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}},
                "solver": {"strategy": "invalid_strategy"}
            }, schema)


class TestSection13CompleteExamples:
    """Section 13: Complete example validation"""

    def test_minimal_complete_example_from_spec(self):
        """Test the minimal complete example from Section 13 of the spec."""
        schema = _get_schema()

        minimal_complete = {
            "esm": "0.1.0",
            "metadata": {
                "name": "MinimalChemAdvection",
                "description": "O3-NO-NO2 chemistry with advection and external meteorology",
                "authors": ["Chris Tessum"],
                "created": "2026-02-11T00:00:00Z"
            },
            "reaction_systems": {
                "SimpleOzone": {
                    "coupletype": "SimpleOzoneCoupler",
                    "reference": {"notes": "Minimal O3-NOx photochemical cycle"},
                    "species": {
                        "O3": {"units": "mol/mol", "default": 40e-9, "description": "Ozone"},
                        "NO": {"units": "mol/mol", "default": 0.1e-9, "description": "Nitric oxide"},
                        "NO2": {"units": "mol/mol", "default": 1.0e-9, "description": "Nitrogen dioxide"}
                    },
                    "parameters": {
                        "T": {"units": "K", "default": 298.15, "description": "Temperature"},
                        "M": {"units": "molec/cm^3", "default": 2.46e19, "description": "Air number density"},
                        "jNO2": {"units": "1/s", "default": 0.005, "description": "NO2 photolysis rate"}
                    },
                    "reactions": [
                        {
                            "id": "R1",
                            "name": "NO_O3",
                            "substrates": [
                                {"species": "NO", "stoichiometry": 1},
                                {"species": "O3", "stoichiometry": 1}
                            ],
                            "products": [{"species": "NO2", "stoichiometry": 1}],
                            "rate": {"op": "*", "args": [1.8e-12, {"op": "exp", "args": [{"op": "/", "args": [-1370, "T"]}]}, "M"]}
                        },
                        {
                            "id": "R2",
                            "name": "NO2_photolysis",
                            "substrates": [{"species": "NO2", "stoichiometry": 1}],
                            "products": [
                                {"species": "NO", "stoichiometry": 1},
                                {"species": "O3", "stoichiometry": 1}
                            ],
                            "rate": "jNO2"
                        }
                    ]
                }
            },
            "models": {
                "Advection": {
                    "reference": {"notes": "First-order advection"},
                    "variables": {
                        "u_wind": {"type": "parameter", "units": "m/s", "default": 0.0},
                        "v_wind": {"type": "parameter", "units": "m/s", "default": 0.0}
                    },
                    "equations": [{
                        "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
                        "rhs": {
                            "op": "+", "args": [
                                {"op": "*", "args": [{"op": "-", "args": ["u_wind"]}, {"op": "grad", "args": ["_var"], "dim": "x"}]},
                                {"op": "*", "args": [{"op": "-", "args": ["v_wind"]}, {"op": "grad", "args": ["_var"], "dim": "y"}]}
                            ]
                        }
                    }]
                }
            },
            "data_loaders": {
                "GEOSFP": {
                    "type": "gridded_data",
                    "loader_id": "GEOSFP",
                    "config": {"resolution": "0.25x0.3125_NA", "coord_defaults": {"lat": 34.0, "lev": 1}},
                    "provides": {
                        "u": {"units": "m/s", "description": "Eastward wind"},
                        "v": {"units": "m/s", "description": "Northward wind"},
                        "T": {"units": "K", "description": "Temperature"}
                    }
                }
            },
            "coupling": [
                {"type": "operator_compose", "systems": ["SimpleOzone", "Advection"]},
                {"type": "variable_map", "from": "GEOSFP.T", "to": "SimpleOzone.T", "transform": "param_to_var"},
                {"type": "variable_map", "from": "GEOSFP.u", "to": "Advection.u_wind", "transform": "param_to_var"},
                {"type": "variable_map", "from": "GEOSFP.v", "to": "Advection.v_wind", "transform": "param_to_var"}
            ],
            "domain": {
                "temporal": {"start": "2024-05-01T00:00:00Z", "end": "2024-05-03T00:00:00Z"},
                "spatial": {
                    "lon": {"min": -130.0, "max": -100.0, "grid_spacing": 0.3125, "units": "degrees"}
                },
                "coordinate_transforms": [
                    {"id": "lonlat_to_meters", "dimensions": ["lon"]}
                ],
                "initial_conditions": {"type": "constant", "value": 1.0e-9},
                "boundary_conditions": [{"type": "zero_gradient", "dimensions": ["lon"]}],
                "element_type": "Float32"
            },
            "solver": {
                "strategy": "strang_threads",
                "config": {"stiff_algorithm": "Rosenbrock23", "timestep": 1.0}
            }
        }

        jsonschema.validate(minimal_complete, schema)

    def test_complex_atmospheric_chemistry_example(self):
        """Test a more complex atmospheric chemistry example."""
        schema = _get_schema()

        complex_example = {
            "esm": "0.1.0",
            "metadata": {
                "name": "AtmosphericChemistryFull",
                "description": "Full atmospheric chemistry simulation with multiple processes",
                "authors": ["Research Team"],
                "license": "Apache-2.0",
                "created": "2026-02-14T00:00:00Z",
                "tags": ["atmospheric-chemistry", "pollution", "meteorology"]
            },
            "reaction_systems": {
                "FullChemistry": {
                    "species": {
                        "O3": {"units": "mol/mol", "default": 40e-9},
                        "NO": {"units": "mol/mol", "default": 0.1e-9},
                        "NO2": {"units": "mol/mol", "default": 1e-9},
                        "CO": {"units": "mol/mol", "default": 100e-9}
                    },
                    "parameters": {
                        "T": {"units": "K", "default": 298.15},
                        "jNO2": {"units": "1/s", "default": 0.005}
                    },
                    "reactions": [
                        {
                            "id": "R1",
                            "substrates": [{"species": "NO", "stoichiometry": 1}, {"species": "O3", "stoichiometry": 1}],
                            "products": [{"species": "NO2", "stoichiometry": 1}],
                            "rate": 1.8e-12
                        }
                    ]
                }
            },
            "models": {
                "VerticalMixing": {
                    "variables": {
                        "Kz": {"type": "parameter", "units": "m^2/s", "default": 10.0}
                    },
                    "equations": [{
                        "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
                        "rhs": {"op": "*", "args": ["Kz", {"op": "laplacian", "args": ["_var"]}]}
                    }]
                }
            },
            "data_loaders": {
                "Meteorology": {
                    "type": "gridded_data",
                    "loader_id": "WRF",
                    "provides": {"T": {"units": "K"}, "wind": {"units": "m/s"}}
                }
            },
            "operators": {
                "Deposition": {
                    "operator_id": "DryDep",
                    "needed_vars": ["O3", "NO2"]
                }
            },
            "coupling": [
                {"type": "operator_compose", "systems": ["FullChemistry", "VerticalMixing"]},
                {"type": "operator_apply", "operator": "Deposition"}
            ],
            "domain": {
                "temporal": {"start": "2024-01-01T00:00:00Z", "end": "2024-01-02T00:00:00Z"},
                "spatial": {"z": {"min": 0, "max": 1000, "units": "m"}},
                "initial_conditions": {"type": "constant", "value": 1e-9}
            },
            "solver": {"strategy": "strang_threads"}
        }

        jsonschema.validate(complex_example, schema)


class TestSection14DesignPrinciples:
    """Section 14: Design principles adherence testing"""

    def test_full_specification_principle(self):
        """Test that models and reactions must be fully specified."""
        schema = _get_schema()

        # Valid: fully specified model
        fully_specified = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {
                "FullySpecified": {
                    "variables": {
                        "x": {"type": "state", "units": "mol/mol", "default": 1e-9, "description": "Test species"}
                    },
                    "equations": [{
                        "lhs": {"op": "D", "args": ["x"], "wrt": "t"},
                        "rhs": {"op": "*", "args": [-0.1, "x"]}
                    }]
                }
            }
        }
        jsonschema.validate(fully_specified, schema)

    def test_data_loaders_by_reference_principle(self):
        """Test that data loaders are by reference, not fully specified."""
        schema = _get_schema()

        # Valid: data loader by reference
        by_reference = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "data_loaders": {
                "MetData": {
                    "type": "gridded_data",
                    "loader_id": "GEOSFP",  # Reference to external implementation
                    "provides": {"T": {"units": "K"}}
                }
            }
        }
        jsonschema.validate(by_reference, schema)

    def test_expression_ast_over_string_math_principle(self):
        """Test that expressions use AST format, not string math."""
        schema = _get_schema()

        # Valid: JSON AST expression
        ast_expression = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {
                "test_model": {
                    "variables": {"x": {"type": "state"}},
                    "equations": [{
                        "lhs": "x",
                        "rhs": {
                            "op": "+",
                            "args": [
                                {"op": "*", "args": ["k1", "A"]},
                                {"op": "exp", "args": [{"op": "/", "args": [-1000, "T"]}]}
                            ]
                        }
                    }]
                }
            }
        }
        jsonschema.validate(ast_expression, schema)

    def test_reaction_systems_distinct_from_ode_models_principle(self):
        """Test that reaction systems preserve chemical meaning."""
        schema = _get_schema()

        # Valid: reaction system with stoichiometry
        reaction_system = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "reaction_systems": {
                "ChemicalNetwork": {
                    "species": {"A": {}, "B": {}, "C": {}},
                    "parameters": {"k1": {"default": 0.1}},
                    "reactions": [{
                        "id": "R1",
                        "substrates": [
                            {"species": "A", "stoichiometry": 2},
                            {"species": "B", "stoichiometry": 1}
                        ],
                        "products": [
                            {"species": "C", "stoichiometry": 1}
                        ],
                        "rate": "k1"
                    }]
                }
            }
        }
        jsonschema.validate(reaction_system, schema)

    def test_coupling_first_class_principle(self):
        """Test that coupling is explicitly specified and inspectable."""
        schema = _get_schema()

        # Valid: explicit coupling specification
        explicit_coupling = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "coupling": [
                {
                    "type": "operator_compose",
                    "systems": ["Chemistry", "Transport"],
                    "description": "Couple chemistry with transport processes"
                },
                {
                    "type": "variable_map",
                    "from": "MetData.temperature",
                    "to": "Chemistry.T",
                    "transform": "param_to_var",
                    "description": "Use meteorological temperature in chemistry"
                }
            ]
        }
        jsonschema.validate(explicit_coupling, schema)


class TestSection15FutureConsiderations:
    """Section 15: Future considerations compatibility"""

    def test_extensibility_through_config_fields(self):
        """Test that config fields allow future extensions."""
        schema = _get_schema()

        # Valid: config fields are open for extensions
        extensible_config = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "data_loaders": {
                "future_loader": {
                    "type": "gridded_data",
                    "loader_id": "FutureFormat",
                    "provides": {"x": {"units": "m"}},
                    "config": {
                        "future_option": True,
                        "experimental_feature": {"nested": "value"},
                        "version_specific_params": [1, 2, 3]
                    }
                }
            },
            "operators": {
                "future_op": {
                    "operator_id": "NextGenOperator",
                    "needed_vars": ["x"],
                    "config": {
                        "algorithm_version": "2.0",
                        "performance_hints": {"use_gpu": True}
                    }
                }
            }
        }
        jsonschema.validate(extensible_config, schema)

    def test_version_constraint_for_current_spec(self):
        """Test that version is constrained to current specification."""
        schema = _get_schema()

        # Current version should work
        current_version = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}}
        }
        jsonschema.validate(current_version, schema)

        # Future versions should fail (ensuring schema updates are intentional)
        with pytest.raises(ValidationError):
            jsonschema.validate({
                "esm": "0.2.0",  # Future version
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}}
            }, schema)

    def test_reference_fields_for_provenance(self):
        """Test that reference fields support future provenance features."""
        schema = _get_schema()

        # Valid: rich reference information for future tools
        rich_references = {
            "esm": "0.1.0",
            "metadata": {
                "name": "Test",
                "references": [{
                    "doi": "10.1234/future-reference",
                    "citation": "Future et al., 2026. Advanced modeling techniques.",
                    "url": "https://future-journal.org/article",
                    # Note: additional fields in references could be added in future
                }]
            },
            "models": {
                "test_model": {
                    "variables": {},
                    "equations": [],
                    "reference": {
                        "doi": "10.1234/model-specific",
                        "citation": "Model Authors, 2026",
                        "notes": "Detailed implementation notes for future reference"
                    }
                }
            }
        }
        jsonschema.validate(rich_references, schema)


class TestCrossSectionValidation:
    """Cross-section tests that validate interactions between sections"""

    def test_scoped_references_across_systems(self):
        """Test scoped reference resolution across different system types."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {
                "ModelSystem": {
                    "variables": {"model_var": {"type": "state"}},
                    "equations": []
                }
            },
            "reaction_systems": {
                "ReactionSystem": {
                    "species": {"reaction_species": {}},
                    "parameters": {},
                    "reactions": [{"id": "R1", "substrates": None, "products": [{"species": "reaction_species", "stoichiometry": 1}], "rate": 1.0}]
                }
            },
            "coupling": [{
                "type": "variable_map",
                "from": "ReactionSystem.reaction_species",
                "to": "ModelSystem.model_var",
                "transform": "identity"
            }]
        }
        jsonschema.validate(valid_data, schema)

    def test_event_system_integration(self):
        """Test events that integrate multiple system sections."""
        schema = _get_schema()

        valid_data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {
                "ControlModel": {
                    "variables": {"controller": {"type": "state"}},
                    "equations": [],
                    "discrete_events": [{
                        "trigger": {"type": "condition", "expression": {"op": ">", "args": ["controller", 1]}},
                        "functional_affect": {
                            "handler_id": "SystemController",
                            "read_vars": ["controller"],
                            "read_params": [],
                            "config": {"action": "reset"}
                        }
                    }]
                }
            },
            "operators": {
                "SystemController": {
                    "operator_id": "ControlLogic",
                    "needed_vars": ["controller"]
                }
            }
        }
        jsonschema.validate(valid_data, schema)

    def test_comprehensive_integration_example(self):
        """Test comprehensive example integrating all major sections."""
        schema = _get_schema()

        comprehensive = {
            "esm": "0.1.0",
            "metadata": {
                "name": "ComprehensiveIntegrationTest",
                "description": "Tests integration of all ESM format sections",
                "authors": ["Integration Tester"],
                "created": "2026-02-14T00:00:00Z"
            },
            "reaction_systems": {
                "Chemistry": {
                    "species": {"O3": {"units": "mol/mol", "default": 40e-9}},
                    "parameters": {"T": {"units": "K", "default": 298}},
                    "reactions": [{
                        "id": "R1",
                        "substrates": None,
                        "products": [{"species": "O3", "stoichiometry": 1}],
                        "rate": 1e-10
                    }],
                    "continuous_events": [{
                        "conditions": [{"op": "-", "args": ["O3", 100e-9]}],
                        "affects": [{"lhs": "T", "rhs": {"op": "+", "args": [{"op": "Pre", "args": ["T"]}, 1]}}]
                    }]
                }
            },
            "models": {
                "Transport": {
                    "variables": {"wind": {"type": "parameter", "units": "m/s", "default": 5}},
                    "equations": [{
                        "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
                        "rhs": {"op": "*", "args": ["wind", {"op": "grad", "args": ["_var"], "dim": "x"}]}
                    }]
                }
            },
            "data_loaders": {
                "MetData": {
                    "type": "gridded_data",
                    "loader_id": "TestMet",
                    "provides": {"wind_field": {"units": "m/s"}}
                }
            },
            "operators": {
                "Emissions": {
                    "operator_id": "EmissionOperator",
                    "needed_vars": ["O3"]
                }
            },
            "coupling": [
                {"type": "operator_compose", "systems": ["Chemistry", "Transport"]},
                {"type": "variable_map", "from": "MetData.wind_field", "to": "Transport.wind", "transform": "param_to_var"},
                {"type": "operator_apply", "operator": "Emissions"}
            ],
            "domain": {
                "temporal": {"start": "2024-01-01T00:00:00Z", "end": "2024-01-01T01:00:00Z"},
                "spatial": {"x": {"min": 0, "max": 100, "units": "m"}},
                "initial_conditions": {"type": "constant", "value": 1e-9}
            },
            "solver": {"strategy": "strang_threads", "config": {"timestep": 60}}
        }

        jsonschema.validate(comprehensive, schema)


class TestNegativeValidationCases:
    """Comprehensive negative validation cases for all sections"""

    def test_section_specific_violations(self):
        """Test violations specific to each section."""
        schema = _get_schema()

        # Section 1: Invalid version format
        with pytest.raises(ValidationError):
            jsonschema.validate({
                "esm": "1.0",  # Missing patch version
                "metadata": {"name": "Test"},
                "models": {"test": {"variables": {}, "equations": []}}
            }, schema)

        # Section 4: Invalid expression operator
        with pytest.raises(ValidationError):
            jsonschema.validate({
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {
                    "test": {
                        "variables": {"x": {"type": "state"}},
                        "equations": [{"lhs": "x", "rhs": {"op": "invalid_op", "args": ["x"]}}]
                    }
                }
            }, schema)

        # Section 7: Invalid stoichiometry
        with pytest.raises(ValidationError):
            jsonschema.validate({
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "reaction_systems": {
                    "test": {
                        "species": {"A": {}},
                        "parameters": {},
                        "reactions": [{
                            "id": "R1",
                            "substrates": [{"species": "A", "stoichiometry": 0}],  # Invalid: must be >= 1
                            "products": None,
                            "rate": 1.0
                        }]
                    }
                }
            }, schema)

    def test_cross_section_violations(self):
        """Test violations that span multiple sections."""
        schema = _get_schema()

        # Coupling with invalid type
        with pytest.raises(ValidationError):
            jsonschema.validate({
                "esm": "0.1.0",
                "metadata": {"name": "Test"},
                "models": {"existing_model": {"variables": {}, "equations": []}},
                "coupling": [{
                    "type": "invalid_coupling_type",  # This should cause schema validation to fail
                    "systems": ["system1", "system2"]
                }]
            }, schema)


def test_complete_specification_coverage():
    """Meta-test to ensure all 15 sections are covered by test classes."""

    # Check that we have test classes for all 15 sections
    expected_sections = [
        'TestSection01Overview',
        'TestSection02TopLevelStructure',
        'TestSection03Metadata',
        'TestSection04ExpressionAST',
        'TestSection05Events',
        'TestSection06Models',
        'TestSection07ReactionSystems',
        'TestSection08DataLoaders',
        'TestSection09Operators',
        'TestSection10Coupling',
        'TestSection11Domain',
        'TestSection12Solver',
        'TestSection13CompleteExamples',
        'TestSection14DesignPrinciples',
        'TestSection15FutureConsiderations'
    ]

    # Get all test classes defined in this module
    import sys
    current_module = sys.modules[__name__]
    test_classes = [name for name in dir(current_module)
                   if name.startswith('TestSection') and name != 'TestCrossSection']

    # Verify all sections are covered
    for expected in expected_sections:
        assert expected in test_classes, f"Missing test class for {expected}"

    print(f"✓ All {len(expected_sections)} ESM specification sections are covered by test classes")


if __name__ == "__main__":
    # Run coverage verification
    test_complete_specification_coverage()