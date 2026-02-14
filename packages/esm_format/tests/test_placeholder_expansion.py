"""Tests for placeholder expansion (_var) functionality."""

import json
import pytest
from esm_format import load
from esm_format.parse import _parse_expression
from esm_format.types import ExprNode, EsmFile


class TestPlaceholderExpansion:
    """Test cases for _var placeholder expansion in ESM format."""

    def test_parse_simple_placeholder(self):
        """Test parsing expression containing _var placeholder."""
        # Simple case: just the placeholder
        expr = _parse_expression("_var")
        assert expr == "_var"

        # In expression node
        expr_data = {
            "op": "D",
            "args": ["_var"],
            "wrt": "t"
        }
        expr = _parse_expression(expr_data)
        assert isinstance(expr, ExprNode)
        assert expr.op == "D"
        assert expr.args == ["_var"]
        assert expr.wrt == "t"

    def test_parse_placeholder_in_complex_expressions(self):
        """Test _var placeholder in complex nested expressions."""
        # Test _var in arithmetic operations
        expr_data = {
            "op": "+",
            "args": [
                {"op": "*", "args": ["k1", "_var"]},
                {"op": "/", "args": ["_var", "tau"]}
            ]
        }
        expr = _parse_expression(expr_data)
        assert isinstance(expr, ExprNode)
        assert expr.op == "+"

        # Check first term: k1 * _var
        first_term = expr.args[0]
        assert isinstance(first_term, ExprNode)
        assert first_term.op == "*"
        assert first_term.args == ["k1", "_var"]

        # Check second term: _var / tau
        second_term = expr.args[1]
        assert isinstance(second_term, ExprNode)
        assert second_term.op == "/"
        assert second_term.args == ["_var", "tau"]

    def test_placeholder_in_spatial_operations(self):
        """Test _var placeholder with spatial operators."""
        # Test with gradient operator
        expr_data = {
            "op": "grad",
            "args": ["_var"],
            "dim": "x"
        }
        expr = _parse_expression(expr_data)
        assert isinstance(expr, ExprNode)
        assert expr.op == "grad"
        assert expr.args == ["_var"]
        assert expr.dim == "x"

        # Test with divergence
        expr_data = {
            "op": "div",
            "args": [{"op": "*", "args": ["u_wind", "_var"]}]
        }
        expr = _parse_expression(expr_data)
        assert isinstance(expr, ExprNode)
        assert expr.op == "div"
        nested = expr.args[0]
        assert nested.args == ["u_wind", "_var"]

    def test_placeholder_in_advection_model(self):
        """Test _var in complete advection model example."""
        advection_model = {
            "esm": "0.1.0",
            "metadata": {"name": "Advection Test"},
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

        json_str = json.dumps(advection_model)
        esm_file = load(json_str)

        assert isinstance(esm_file, EsmFile)
        assert len(esm_file.models) == 1

        model = esm_file.models[0]
        assert model.name == "Advection"
        assert len(model.equations) == 1

        equation = model.equations[0]

        # Check LHS has _var placeholder
        lhs = equation.lhs
        assert isinstance(lhs, ExprNode)
        assert lhs.op == "D"
        assert lhs.args == ["_var"]
        assert lhs.wrt == "t"

        # Check RHS has _var placeholders in gradients
        rhs = equation.rhs
        assert isinstance(rhs, ExprNode)
        assert rhs.op == "+"

        # First term: -u_wind * grad(_var, x)
        term1 = rhs.args[0]
        grad_x = term1.args[1]
        assert grad_x.op == "grad"
        assert grad_x.args == ["_var"]
        assert grad_x.dim == "x"

        # Second term: -v_wind * grad(_var, y)
        term2 = rhs.args[1]
        grad_y = term2.args[1]
        assert grad_y.op == "grad"
        assert grad_y.args == ["_var"]
        assert grad_y.dim == "y"

    def test_multiple_placeholders_same_expression(self):
        """Test multiple _var placeholders in the same expression."""
        expr_data = {
            "op": "*",
            "args": [
                {"op": "+", "args": ["_var", 1]},
                {"op": "-", "args": ["_var", "background"]}
            ]
        }
        expr = _parse_expression(expr_data)

        # Both sub-expressions should contain _var
        left_term = expr.args[0]
        right_term = expr.args[1]

        assert left_term.args == ["_var", 1]
        assert right_term.args == ["_var", "background"]

    def test_placeholder_with_chemical_kinetics(self):
        """Test _var placeholder in chemical kinetics context."""
        # Example: first-order decay with _var
        expr_data = {
            "op": "*",
            "args": [
                {"op": "-", "args": ["k_loss"]},
                "_var"
            ]
        }
        expr = _parse_expression(expr_data)
        assert isinstance(expr, ExprNode)
        assert expr.op == "*"
        assert expr.args[1] == "_var"

        # Example: temperature-dependent rate with _var
        expr_data = {
            "op": "*",
            "args": [
                {
                    "op": "*",
                    "args": [
                        "A",
                        {
                            "op": "exp",
                            "args": [
                                {"op": "/", "args": [{"op": "-", "args": ["Ea"]}, "T"]}
                            ]
                        }
                    ]
                },
                "_var"
            ]
        }
        expr = _parse_expression(expr_data)
        assert expr.args[1] == "_var"

    def test_placeholder_validation_edge_cases(self):
        """Test edge cases and validation for _var usage."""
        # Test _var as only argument
        expr = _parse_expression("_var")
        assert expr == "_var"

        # Test _var in single-argument operation
        expr_data = {"op": "exp", "args": ["_var"]}
        expr = _parse_expression(expr_data)
        assert expr.args == ["_var"]

        # Test _var mixed with constants
        expr_data = {"op": "*", "args": [2.5, "_var"]}
        expr = _parse_expression(expr_data)
        assert expr.args == [2.5, "_var"]

        # Test _var mixed with other variables
        expr_data = {"op": "+", "args": ["_var", "constant_term", "other_var"]}
        expr = _parse_expression(expr_data)
        assert "_var" in expr.args
        assert "constant_term" in expr.args
        assert "other_var" in expr.args

    def test_placeholder_in_operator_models(self):
        """Test _var in operator-style models that will be composed."""
        # Generic diffusion operator model
        diffusion_model = {
            "esm": "0.1.0",
            "metadata": {"name": "Generic Diffusion"},
            "models": {
                "Diffusion": {
                    "variables": {
                        "K_diff": {"type": "parameter", "units": "m^2/s", "default": 1.0}
                    },
                    "equations": [
                        {
                            "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
                            "rhs": {
                                "op": "*",
                                "args": [
                                    "K_diff",
                                    {"op": "laplacian", "args": ["_var"]}
                                ]
                            }
                        }
                    ]
                }
            }
        }

        json_str = json.dumps(diffusion_model)
        esm_file = load(json_str)

        model = esm_file.models[0]
        equation = model.equations[0]

        # Verify placeholder in LHS
        assert equation.lhs.args == ["_var"]

        # Verify placeholder in RHS laplacian
        laplacian_term = equation.rhs.args[1]
        assert laplacian_term.op == "laplacian"
        assert laplacian_term.args == ["_var"]

    def test_placeholder_roundtrip_consistency(self):
        """Test that _var placeholders survive parse->serialize->parse cycle."""
        from esm_format.serialize import _serialize_expression

        # Create expression with _var
        expr_data = {
            "op": "D",
            "args": ["_var"],
            "wrt": "t"
        }

        # Parse it
        parsed = _parse_expression(expr_data)

        # Serialize it back
        serialized = _serialize_expression(parsed)

        # Parse again
        reparsed = _parse_expression(serialized)

        # Should be identical
        assert reparsed.op == parsed.op
        assert reparsed.args == parsed.args
        assert reparsed.wrt == parsed.wrt

    def test_placeholder_documentation_examples(self):
        """Test examples from the ESM specification documentation."""
        # Example from spec: advection equation with _var
        spec_example = {
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

        # Parse LHS
        lhs = _parse_expression(spec_example["lhs"])
        assert isinstance(lhs, ExprNode)
        assert lhs.args == ["_var"]

        # Parse RHS
        rhs = _parse_expression(spec_example["rhs"])

        # Verify both gradient terms contain _var
        term1_grad = rhs.args[0].args[1]
        term2_grad = rhs.args[1].args[1]

        assert term1_grad.args == ["_var"]
        assert term1_grad.dim == "x"
        assert term2_grad.args == ["_var"]
        assert term2_grad.dim == "y"

    def test_nested_placeholder_expressions(self):
        """Test deeply nested expressions with _var placeholders."""
        # Complex nested example: d/dt(_var) = f(grad(div(_var)))
        complex_expr = {
            "op": "D",
            "args": [
                {
                    "op": "*",
                    "args": [
                        "coeff",
                        {
                            "op": "grad",
                            "args": [
                                {
                                    "op": "div",
                                    "args": [
                                        {
                                            "op": "*",
                                            "args": ["velocity_field", "_var"]
                                        }
                                    ]
                                }
                            ],
                            "dim": "x"
                        }
                    ]
                }
            ],
            "wrt": "t"
        }

        expr = _parse_expression(complex_expr)

        # Navigate down the nested structure to find _var
        multiply_node = expr.args[0]
        grad_node = multiply_node.args[1]
        div_node = grad_node.args[0]
        inner_multiply = div_node.args[0]

        assert inner_multiply.args == ["velocity_field", "_var"]

    def test_placeholder_type_consistency(self):
        """Test that _var maintains string type throughout parsing."""
        test_cases = [
            "_var",
            {"op": "identity", "args": ["_var"]},
            {"op": "+", "args": ["_var", 0]},
            {"op": "*", "args": [1, "_var"]},
            {"op": "D", "args": ["_var"], "wrt": "t"},
            {"op": "grad", "args": ["_var"], "dim": "x"}
        ]

        for case in test_cases:
            expr = _parse_expression(case)
            if isinstance(expr, str):
                assert expr == "_var"
            else:
                # Find _var in the expression tree
                def find_var_placeholder(node):
                    if isinstance(node, str) and node == "_var":
                        return True
                    elif isinstance(node, ExprNode):
                        return any(find_var_placeholder(arg) for arg in node.args)
                    return False

                assert find_var_placeholder(expr), f"_var not found in {case}"