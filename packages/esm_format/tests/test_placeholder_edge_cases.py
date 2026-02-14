"""Edge cases and integration tests for _var placeholder expansion."""

import json
import pytest
from esm_format import load
from esm_format.parse import _parse_expression
from esm_format.serialize import _serialize_expression
from esm_format.types import ExprNode, EsmFile


class TestPlaceholderEdgeCases:
    """Test edge cases, validation, and integration scenarios for _var placeholders."""

    def test_placeholder_serialization_roundtrip(self):
        """Test complete roundtrip: parse -> serialize -> parse for _var expressions."""
        test_expressions = [
            "_var",
            {"op": "D", "args": ["_var"], "wrt": "t"},
            {
                "op": "+",
                "args": [
                    {"op": "*", "args": ["k1", "_var"]},
                    {"op": "grad", "args": ["_var"], "dim": "x"}
                ]
            }
        ]

        for original_expr in test_expressions:
            # Parse original
            parsed = _parse_expression(original_expr)

            # Serialize back to JSON
            serialized = _serialize_expression(parsed)

            # Parse again
            reparsed = _parse_expression(serialized)

            # Compare structure
            if isinstance(original_expr, str):
                assert reparsed == "_var"
            else:
                # For complex expressions, check key properties
                assert type(parsed) == type(reparsed)
                if hasattr(parsed, 'op'):
                    assert parsed.op == reparsed.op
                if hasattr(parsed, 'args'):
                    assert parsed.args == reparsed.args

    def test_placeholder_with_complex_nesting(self):
        """Test deeply nested expressions with multiple _var instances."""
        complex_expr = {
            "op": "+",
            "args": [
                {
                    "op": "*",
                    "args": [
                        {
                            "op": "D",
                            "args": [
                                {
                                    "op": "/",
                                    "args": [
                                        "_var",
                                        {"op": "+", "args": ["_var", "K"]}
                                    ]
                                }
                            ],
                            "wrt": "t"
                        },
                        "alpha"
                    ]
                },
                {
                    "op": "grad",
                    "args": [
                        {
                            "op": "*",
                            "args": [
                                "D_eff",
                                {"op": "grad", "args": ["_var"]}
                            ]
                        }
                    ]
                }
            ]
        }

        expr = _parse_expression(complex_expr)

        # Verify multiple _var instances are preserved
        def count_var_placeholders(node):
            if isinstance(node, str) and node == "_var":
                return 1
            elif isinstance(node, ExprNode):
                return sum(count_var_placeholders(arg) for arg in node.args)
            return 0

        var_count = count_var_placeholders(expr)
        assert var_count == 3, f"Expected 3 _var placeholders, found {var_count}"

    def test_placeholder_operator_composition_patterns(self):
        """Test typical patterns used in operator composition."""
        # Pattern 1: Simple advection
        advection = {
            "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
            "rhs": {
                "op": "*",
                "args": [
                    {"op": "-", "args": ["velocity"]},
                    {"op": "grad", "args": ["_var"]}
                ]
            }
        }

        lhs = _parse_expression(advection["lhs"])
        rhs = _parse_expression(advection["rhs"])

        assert lhs.args == ["_var"]
        assert rhs.args[1].args == ["_var"]

        # Pattern 2: Diffusion
        diffusion = {
            "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
            "rhs": {
                "op": "*",
                "args": ["D_coeff", {"op": "laplacian", "args": ["_var"]}]
            }
        }

        lhs = _parse_expression(diffusion["lhs"])
        rhs = _parse_expression(diffusion["rhs"])

        assert lhs.args == ["_var"]
        assert rhs.args[1].args == ["_var"]

        # Pattern 3: First-order reaction
        reaction = {
            "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
            "rhs": {
                "op": "*",
                "args": [{"op": "-", "args": ["k_rate"]}, "_var"]
            }
        }

        lhs = _parse_expression(reaction["lhs"])
        rhs = _parse_expression(reaction["rhs"])

        assert lhs.args == ["_var"]
        assert rhs.args[1] == "_var"

    def test_placeholder_with_physical_constants(self):
        """Test _var expressions that include physical constants."""
        # Gas law expression: P = (rho / M) * R * T
        # where rho (_var) is mass concentration
        gas_law_expr = {
            "op": "*",
            "args": [
                {
                    "op": "*",
                    "args": [
                        {"op": "/", "args": ["_var", "molecular_weight"]},
                        "R_gas"
                    ]
                },
                "temperature"
            ]
        }

        expr = _parse_expression(gas_law_expr)
        ratio_term = expr.args[0].args[0]
        assert ratio_term.args[0] == "_var"

        # Arrhenius rate with _var as concentration
        arrhenius_expr = {
            "op": "*",
            "args": [
                {
                    "op": "*",
                    "args": [
                        "A_factor",
                        {
                            "op": "exp",
                            "args": [
                                {"op": "/", "args": [{"op": "-", "args": ["E_activation"]}, "RT"]}
                            ]
                        }
                    ]
                },
                "_var"
            ]
        }

        expr = _parse_expression(arrhenius_expr)
        assert expr.args[1] == "_var"

    def test_placeholder_dimensional_consistency_examples(self):
        """Test _var in expressions that maintain dimensional consistency."""
        # Examples that would be dimensionally consistent in real applications

        # Mass balance: d(mass)/dt = sources - sinks
        mass_balance = {
            "op": "D",
            "args": [
                {
                    "op": "+",
                    "args": ["_var", "background_concentration"]
                }
            ],
            "wrt": "t"
        }

        expr = _parse_expression(mass_balance)
        concentration_sum = expr.args[0]
        assert concentration_sum.args[0] == "_var"

        # Energy balance with _var as temperature
        energy_balance = {
            "op": "*",
            "args": [
                "heat_capacity",
                {"op": "D", "args": ["_var"], "wrt": "t"}
            ]
        }

        expr = _parse_expression(energy_balance)
        temp_derivative = expr.args[1]
        assert temp_derivative.args == ["_var"]

    def test_placeholder_error_propagation(self):
        """Test that _var preserves error information in complex expressions."""
        # These expressions could potentially cause runtime errors but should parse correctly

        # Division by expression involving _var
        risky_division = {
            "op": "/",
            "args": [
                "numerator",
                {"op": "+", "args": ["_var", "small_constant"]}
            ]
        }

        expr = _parse_expression(risky_division)
        denominator = expr.args[1]
        assert denominator.args[0] == "_var"

        # Logarithm of expression with _var
        log_expr = {
            "op": "log",
            "args": [
                {"op": "+", "args": ["_var", "positive_offset"]}
            ]
        }

        expr = _parse_expression(log_expr)
        log_arg = expr.args[0]
        assert log_arg.args[0] == "_var"

    def test_placeholder_with_conditional_expressions(self):
        """Test _var in conditional (ifelse) expressions."""
        conditional_expr = {
            "op": "ifelse",
            "args": [
                {"op": ">", "args": ["_var", "threshold"]},
                {"op": "*", "args": ["high_rate", "_var"]},
                {"op": "*", "args": ["low_rate", "_var"]}
            ]
        }

        expr = _parse_expression(conditional_expr)

        # Check condition: _var > threshold
        condition = expr.args[0]
        assert condition.args[0] == "_var"

        # Check true branch: high_rate * _var
        true_branch = expr.args[1]
        assert true_branch.args[1] == "_var"

        # Check false branch: low_rate * _var
        false_branch = expr.args[2]
        assert false_branch.args[1] == "_var"

    def test_placeholder_in_complete_system_models(self):
        """Test _var in complete, realistic system models."""
        # Complete atmospheric chemistry operator
        atm_chem_system = {
            "esm": "0.1.0",
            "metadata": {"name": "Atmospheric Chemistry Operator"},
            "models": {
                "PhotoChemistry": {
                    "variables": {
                        "j_rate": {"type": "parameter", "units": "1/s", "default": 0.001},
                        "T": {"type": "parameter", "units": "K", "default": 298.15},
                        "pressure": {"type": "parameter", "units": "Pa", "default": 101325.0}
                    },
                    "equations": [
                        {
                            "_comment": "Photochemical loss with temperature dependence",
                            "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
                            "rhs": {
                                "op": "*",
                                "args": [
                                    {
                                        "op": "*",
                                        "args": [
                                            {"op": "-", "args": ["j_rate"]},
                                            {
                                                "op": "exp",
                                                "args": [
                                                    {
                                                        "op": "/",
                                                        "args": [
                                                            {"op": "-", "args": [1000.0]},
                                                            "T"
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    "_var"
                                ]
                            }
                        }
                    ]
                }
            }
        }

        json_str = json.dumps(atm_chem_system)
        esm_file = load(json_str)

        model = esm_file.models[0]
        equation = model.equations[0]

        # Verify the complete structure with _var
        assert equation.lhs.args == ["_var"]
        assert equation.rhs.args[1] == "_var"

    def test_placeholder_validation_against_schema(self):
        """Test that _var expressions validate against the ESM schema."""
        # Create minimal valid ESM with _var
        valid_esm = {
            "esm": "0.1.0",
            "metadata": {"name": "Validation Test"},
            "models": {
                "TestModel": {
                    "variables": {
                        "param1": {"type": "parameter", "units": "1", "default": 1.0}
                    },
                    "equations": [
                        {
                            "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
                            "rhs": {"op": "*", "args": ["param1", "_var"]}
                        }
                    ]
                }
            }
        }

        # This should not raise a ValidationError
        json_str = json.dumps(valid_esm)
        esm_file = load(json_str)

        assert isinstance(esm_file, EsmFile)
        assert len(esm_file.models) == 1

    def test_placeholder_string_consistency(self):
        """Test that _var maintains exact string consistency throughout processing."""
        # Test various ways _var might appear
        expressions = [
            "_var",
            {"op": "+", "args": ["_var", "_var"]},
            {"op": "*", "args": [2.0, "_var"]},
            {"op": "D", "args": ["_var"], "wrt": "t"},
            {"op": "grad", "args": ["_var"], "dim": "x"}
        ]

        for expr_data in expressions:
            expr = _parse_expression(expr_data)

            # Find all string arguments and verify exact match
            def find_all_strings(node):
                strings = []
                if isinstance(node, str):
                    strings.append(node)
                elif isinstance(node, ExprNode):
                    for arg in node.args:
                        strings.extend(find_all_strings(arg))
                return strings

            all_strings = find_all_strings(expr)
            var_strings = [s for s in all_strings if s == "_var"]

            # All _var instances should be identical strings
            for var_str in var_strings:
                assert var_str == "_var"
                assert type(var_str) == str
                assert len(var_str) == 4
                assert var_str.startswith("_")

    def test_placeholder_performance_patterns(self):
        """Test _var in expressions that represent common performance-sensitive patterns."""
        # Large expression trees that might appear in real models
        large_expr = {
            "op": "+",
            "args": [
                {"op": "*", "args": ["c1", "_var"]},
                {"op": "*", "args": ["c2", {"op": "^", "args": ["_var", 2]}]},
                {"op": "*", "args": ["c3", {"op": "^", "args": ["_var", 3]}]},
                {"op": "*", "args": ["c4", {"op": "exp", "args": [{"op": "/", "args": ["_var", "scale"]}]}]},
                {"op": "*", "args": ["c5", {"op": "log", "args": [{"op": "+", "args": ["_var", 1]}]}]}
            ]
        }

        expr = _parse_expression(large_expr)

        # Count _var occurrences
        def count_vars(node):
            if isinstance(node, str) and node == "_var":
                return 1
            elif isinstance(node, ExprNode):
                return sum(count_vars(arg) for arg in node.args)
            return 0

        var_count = count_vars(expr)
        assert var_count == 5

    def test_placeholder_integration_with_existing_tests(self):
        """Ensure _var tests integrate well with existing test infrastructure."""
        # Load an existing test case and verify it doesn't break
        from tests.test_parse import test_parse_simple_expression

        # Run existing test
        test_parse_simple_expression()

        # Verify our _var additions don't interfere
        simple_var_expr = _parse_expression("_var")
        assert simple_var_expr == "_var"

        # Test mixed expressions with existing patterns
        mixed_expr = {
            "op": "+",
            "args": [
                {"op": "*", "args": ["x", 2]},  # existing pattern
                {"op": "*", "args": ["_var", 3]}  # new pattern
            ]
        }

        expr = _parse_expression(mixed_expr)
        assert expr.args[0].args == ["x", 2]
        assert expr.args[1].args == ["_var", 3]

    def test_placeholder_documentation_compliance(self):
        """Test that _var usage complies with ESM specification documentation."""
        # Example directly from the specification
        spec_advection = {
            "esm": "0.1.0",
            "metadata": {
                "name": "Advection",
                "description": "First-order advection",
                "authors": ["Test Author"]
            },
            "models": {
                "Advection": {
                    "variables": {
                        "u_wind": {"type": "parameter", "units": "m/s", "default": 0.0},
                        "v_wind": {"type": "parameter", "units": "m/s", "default": 0.0}
                    },
                    "equations": [
                        {
                            "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
                            "rhs": {
                                "op": "+",
                                "args": [
                                    {
                                        "op": "*",
                                        "args": [
                                            {"op": "-", "args": ["u_wind"]},
                                            {"op": "grad", "args": ["_var"], "dim": "x"}
                                        ]
                                    },
                                    {
                                        "op": "*",
                                        "args": [
                                            {"op": "-", "args": ["v_wind"]},
                                            {"op": "grad", "args": ["_var"], "dim": "y"}
                                        ]
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }

        json_str = json.dumps(spec_advection)
        esm_file = load(json_str)

        # Verify it parses correctly and maintains _var placeholders
        model = esm_file.models[0]
        equation = model.equations[0]

        assert equation.lhs.args == ["_var"]

        rhs_terms = equation.rhs.args
        x_grad = rhs_terms[0].args[1]
        y_grad = rhs_terms[1].args[1]

        assert x_grad.args == ["_var"]
        assert x_grad.dim == "x"
        assert y_grad.args == ["_var"]
        assert y_grad.dim == "y"