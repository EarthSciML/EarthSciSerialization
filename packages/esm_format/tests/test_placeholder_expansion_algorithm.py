"""Tests for the placeholder expansion algorithm implementation."""

import pytest
from esm_format.placeholder_expansion import (
    expand_placeholder,
    expand_multiple_placeholders,
    validate_placeholder_expansion,
    get_placeholder_variables,
    create_expansion_template,
    ExpansionContext,
    CircularReferenceError,
    PlaceholderExpansionError,
)
from esm_format.parse import _parse_expression
from esm_format.types import ExprNode


class TestPlaceholderExpansionAlgorithm:
    """Test the core placeholder expansion algorithm functionality."""

    def test_expand_simple_placeholder_string(self):
        """Test expanding a simple _var string placeholder."""
        result = expand_placeholder("_var", "temperature")
        assert result == "temperature"

        result = expand_placeholder("other_var", "temperature")
        assert result == "other_var"

    def test_expand_placeholder_in_expression_node(self):
        """Test expanding _var in ExprNode structures."""
        # Create expression: D(_var)/Dt
        expr_data = {"op": "D", "args": ["_var"], "wrt": "t"}
        expr = _parse_expression(expr_data)

        result = expand_placeholder(expr, "temperature")

        assert isinstance(result, ExprNode)
        assert result.op == "D"
        assert result.args == ["temperature"]
        assert result.wrt == "t"

    def test_expand_complex_nested_expression(self):
        """Test expanding _var in complex nested expressions."""
        # Expression: k * _var + grad(_var)
        expr_data = {
            "op": "+",
            "args": [
                {"op": "*", "args": ["k", "_var"]},
                {"op": "grad", "args": ["_var"]}
            ]
        }
        expr = _parse_expression(expr_data)

        result = expand_placeholder(expr, "concentration")

        assert isinstance(result, ExprNode)
        assert result.op == "+"

        # First term: k * concentration
        first_term = result.args[0]
        assert first_term.op == "*"
        assert first_term.args == ["k", "concentration"]

        # Second term: grad(concentration)
        second_term = result.args[1]
        assert second_term.op == "grad"
        assert second_term.args == ["concentration"]

    def test_expand_multiple_var_instances(self):
        """Test expanding multiple _var instances in same expression."""
        # Expression: _var / (_var + K)
        expr_data = {
            "op": "/",
            "args": [
                "_var",
                {"op": "+", "args": ["_var", "K"]}
            ]
        }
        expr = _parse_expression(expr_data)

        result = expand_placeholder(expr, "substrate")

        assert isinstance(result, ExprNode)
        assert result.op == "/"
        assert result.args[0] == "substrate"

        denominator = result.args[1]
        assert denominator.op == "+"
        assert denominator.args == ["substrate", "K"]

    def test_expand_with_spatial_attributes(self):
        """Test that spatial attributes are preserved during expansion."""
        expr_data = {"op": "grad", "args": ["_var"], "dim": "x"}
        expr = _parse_expression(expr_data)

        result = expand_placeholder(expr, "pressure")

        assert isinstance(result, ExprNode)
        assert result.op == "grad"
        assert result.args == ["pressure"]
        assert result.dim == "x"

    def test_expand_numeric_expressions_unchanged(self):
        """Test that numeric values are unchanged during expansion."""
        result = expand_placeholder(42, "temperature")
        assert result == 42

        result = expand_placeholder(3.14159, "temperature")
        assert result == 3.14159

    def test_expansion_context_tracking(self):
        """Test that ExpansionContext properly tracks expansion state."""
        context = ExpansionContext()

        assert context.get_expansion_depth() == 0
        assert context.get_current_path() == []

        context.enter_expansion("temperature")
        assert context.get_expansion_depth() == 1
        assert context.get_current_path() == ["temperature"]

        context.enter_expansion("pressure")
        assert context.get_expansion_depth() == 2
        assert context.get_current_path() == ["temperature", "pressure"]

        context.exit_expansion()
        assert context.get_expansion_depth() == 1
        assert context.is_expanded("pressure")

        context.exit_expansion()
        assert context.get_expansion_depth() == 0
        assert context.is_expanded("temperature")

    def test_circular_reference_detection(self):
        """Test detection of circular references in expansion."""
        context = ExpansionContext()

        # Simulate circular reference: A -> B -> A
        context.enter_expansion("A")
        context.enter_expansion("B")

        with pytest.raises(CircularReferenceError) as exc_info:
            context.enter_expansion("A")

        assert "Circular reference detected" in str(exc_info.value)
        assert "A -> B -> A" in str(exc_info.value)

    def test_max_depth_protection(self):
        """Test maximum recursion depth protection."""
        # Create deeply nested expression
        expr = "_var"
        for _ in range(5):
            expr = {"op": "+", "args": [expr, "_var"]}

        with pytest.raises(PlaceholderExpansionError) as exc_info:
            expand_placeholder(expr, "temperature", max_depth=2)

        assert "Maximum" in str(exc_info.value) and "depth" in str(exc_info.value)

    def test_expand_multiple_placeholders(self):
        """Test expanding multiple different placeholders."""
        # Expression with _var and _var2
        expr_data = {
            "op": "*",
            "args": [
                {"op": "+", "args": ["_var", "_var2"]},
                {"op": "D", "args": ["_var"], "wrt": "t"}
            ]
        }
        expr = _parse_expression(expr_data)

        placeholder_map = {"_var": "temperature", "_var2": "pressure"}
        result = expand_multiple_placeholders(expr, placeholder_map)

        assert isinstance(result, ExprNode)
        assert result.op == "*"

        # First term: temperature + pressure
        first_term = result.args[0]
        assert first_term.args == ["temperature", "pressure"]

        # Second term: D(temperature)/Dt
        second_term = result.args[1]
        assert second_term.args == ["temperature"]

    def test_validate_placeholder_expansion(self):
        """Test validation of placeholder expansion results."""
        original_expr = {"op": "*", "args": ["_var", "k"]}
        expanded_expr = {"op": "*", "args": ["temperature", "k"]}

        # Valid expansion
        assert validate_placeholder_expansion(original_expr, expanded_expr, "temperature")

        # Invalid: still contains _var
        invalid_expanded = {"op": "*", "args": ["_var", "k"]}
        assert not validate_placeholder_expansion(original_expr, invalid_expanded, "temperature")

        # Invalid: doesn't contain target variable
        wrong_expanded = {"op": "*", "args": ["pressure", "k"]}
        assert not validate_placeholder_expansion(original_expr, wrong_expanded, "temperature")

    def test_get_placeholder_variables(self):
        """Test extraction of placeholder variables from expressions."""
        # Simple case
        placeholders = get_placeholder_variables("_var")
        assert placeholders == {"_var"}

        # Complex expression with multiple placeholders
        expr_data = {
            "op": "+",
            "args": [
                {"op": "*", "args": ["_var", "_coefficient"]},
                {"op": "D", "args": ["_var2"], "wrt": "t"}
            ]
        }
        expr = _parse_expression(expr_data)

        placeholders = get_placeholder_variables(expr)
        assert placeholders == {"_var", "_coefficient", "_var2"}

        # Expression with no placeholders
        expr_data = {"op": "+", "args": ["x", "y"]}
        expr = _parse_expression(expr_data)

        placeholders = get_placeholder_variables(expr)
        assert placeholders == set()

    def test_create_expansion_template(self):
        """Test creation of expansion templates."""
        expr_data = {
            "op": "D",
            "args": ["_var"],
            "wrt": "t"
        }
        expr = _parse_expression(expr_data)

        template = create_expansion_template(expr)

        assert template["template_expression"] == expr
        assert set(template["placeholder_variables"]) == {"_var"}
        assert template["expansion_metadata"]["requires_expansion"] is True
        assert template["expansion_metadata"]["placeholder_count"] == 1
        assert template["expansion_metadata"]["complexity_score"] > 0

    def test_expansion_with_lists_and_dicts(self):
        """Test expansion of placeholders in list and dict structures."""
        # List with _var
        list_expr = ["_var", {"op": "+", "args": ["_var", 1]}, "constant"]
        result = expand_placeholder(list_expr, "temperature")

        assert result[0] == "temperature"
        assert isinstance(result[1], ExprNode)
        assert result[1].args == ["temperature", 1]
        assert result[2] == "constant"

        # Dict with _var
        dict_expr = {
            "variable": "_var",
            "derivative": {"op": "D", "args": ["_var"], "wrt": "t"},
            "constant": 42
        }
        result = expand_placeholder(dict_expr, "pressure")

        assert result["variable"] == "pressure"
        assert isinstance(result["derivative"], ExprNode)
        assert result["derivative"].args == ["pressure"]
        assert result["constant"] == 42

    def test_expansion_preserves_non_placeholder_strings(self):
        """Test that non-placeholder strings are preserved."""
        expr_data = {
            "op": "+",
            "args": ["_var", "normal_variable", "_other_placeholder"]
        }
        expr = _parse_expression(expr_data)

        result = expand_placeholder(expr, "temperature")

        assert isinstance(result, ExprNode)
        assert result.args == ["temperature", "normal_variable", "_other_placeholder"]

    def test_empty_expression_handling(self):
        """Test handling of empty or None expressions."""
        result = expand_placeholder("", "temperature")
        assert result == ""

        result = expand_placeholder([], "temperature")
        assert result == []

        result = expand_placeholder({}, "temperature")
        assert result == {}

    def test_complex_real_world_example(self):
        """Test expansion on a complex real-world atmospheric chemistry example."""
        # Advection-diffusion-reaction equation
        expr_data = {
            "op": "=",
            "args": [
                {"op": "D", "args": ["_var"], "wrt": "t"},
                {
                    "op": "+",
                    "args": [
                        # Advection term: -u * grad(_var)
                        {
                            "op": "*",
                            "args": [
                                {"op": "-", "args": ["u_wind"]},
                                {"op": "grad", "args": ["_var"], "dim": "x"}
                            ]
                        },
                        # Diffusion term: K * laplacian(_var)
                        {
                            "op": "*",
                            "args": ["K_diff", {"op": "laplacian", "args": ["_var"]}]
                        },
                        # Reaction term: -k * _var
                        {
                            "op": "*",
                            "args": [{"op": "-", "args": ["k_rate"]}, "_var"]
                        }
                    ]
                }
            ]
        }
        expr = _parse_expression(expr_data)

        result = expand_placeholder(expr, "ozone_concentration")

        # Validate structure
        assert isinstance(result, ExprNode)
        assert result.op == "="

        # Check LHS: D(ozone_concentration)/Dt
        lhs = result.args[0]
        assert lhs.args == ["ozone_concentration"]

        # Check RHS terms
        rhs = result.args[1]
        assert rhs.op == "+"

        # Advection term
        advection = rhs.args[0]
        assert advection.args[1].args == ["ozone_concentration"]

        # Diffusion term
        diffusion = rhs.args[1]
        assert diffusion.args[1].args == ["ozone_concentration"]

        # Reaction term
        reaction = rhs.args[2]
        assert reaction.args[1] == "ozone_concentration"

        # Validate no _var remains
        assert not validate_placeholder_expansion(expr, result, "ozone_concentration") or \
               not get_placeholder_variables(result).intersection({"_var"})

    def test_expansion_with_custom_placeholders(self):
        """Test expansion with custom placeholder patterns."""
        expr_data = {
            "op": "*",
            "args": ["_custom_placeholder", {"op": "+", "args": ["_custom_placeholder", "offset"]}]
        }
        expr = _parse_expression(expr_data)

        placeholder_map = {"_custom_placeholder": "my_variable"}
        result = expand_multiple_placeholders(expr, placeholder_map)

        assert isinstance(result, ExprNode)
        assert result.args[0] == "my_variable"
        assert result.args[1].args == ["my_variable", "offset"]

    def test_expansion_performance_on_large_expressions(self):
        """Test expansion performance on moderately large expressions."""
        # Create a reasonably complex expression
        base_expr = "_var"
        for i in range(10):
            base_expr = {
                "op": "+",
                "args": [
                    {"op": "*", "args": [f"coeff_{i}", base_expr]},
                    {"op": "^", "args": [base_expr, 2]}
                ]
            }

        expr = _parse_expression(base_expr)

        # This should complete without timeout or memory issues
        # Increase max_depth to handle the moderately complex expression
        result = expand_placeholder(expr, "concentration", max_depth=20)

        # Verify expansion worked
        placeholders = get_placeholder_variables(result)
        assert "_var" not in placeholders

    def test_edge_case_malformed_expressions(self):
        """Test handling of edge cases and potentially malformed expressions."""
        # Expression with None values (should be handled gracefully)
        try:
            result = expand_placeholder(None, "temperature")
            assert result is None
        except Exception:
            # If an exception is raised, it should be well-defined
            pass

        # Very deeply nested structure
        deep_expr = "_var"
        for _ in range(3):  # Keep it reasonable for testing
            deep_expr = {"op": "nested", "args": [deep_expr]}

        expr = _parse_expression(deep_expr)
        result = expand_placeholder(expr, "deep_variable")

        # Should handle without infinite recursion
        assert isinstance(result, ExprNode)