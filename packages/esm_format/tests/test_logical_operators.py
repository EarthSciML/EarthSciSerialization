"""
Test cases for logical operators.
"""

import pytest
import numpy as np
import warnings
from unittest.mock import patch

from esm_format.types import Operator, OperatorType
from esm_format.logical_operators import (
    AndOperator,
    OrOperator,
    NotOperator,
    EqualOperator,
    NotEqualOperator,
    LessThanOperator,
    LessThanOrEqualOperator,
    GreaterThanOperator,
    GreaterThanOrEqualOperator,
    _coerce_to_boolean,
    _ensure_comparable,
    LogicalOperatorConfig
)
from esm_format.operator_registry import get_registry


class TestBooleanCoercion:
    """Test cases for boolean type coercion."""

    def test_coerce_boolean_true(self):
        """Test coercion of True."""
        assert _coerce_to_boolean(True) is True

    def test_coerce_boolean_false(self):
        """Test coercion of False."""
        assert _coerce_to_boolean(False) is False

    def test_coerce_int_truthy(self):
        """Test coercion of truthy integers."""
        assert _coerce_to_boolean(1) is True
        assert _coerce_to_boolean(-1) is True
        assert _coerce_to_boolean(42) is True

    def test_coerce_int_falsy(self):
        """Test coercion of falsy integers."""
        assert _coerce_to_boolean(0) is False

    def test_coerce_float_truthy(self):
        """Test coercion of truthy floats."""
        assert _coerce_to_boolean(1.0) is True
        assert _coerce_to_boolean(-1.5) is True
        assert _coerce_to_boolean(0.1) is True

    def test_coerce_float_falsy(self):
        """Test coercion of falsy floats."""
        assert _coerce_to_boolean(0.0) is False

    def test_coerce_string_truthy(self):
        """Test coercion of truthy strings."""
        assert _coerce_to_boolean("hello") is True
        assert _coerce_to_boolean("false") is True  # Non-empty string is True
        assert _coerce_to_boolean(" ") is True

    def test_coerce_string_falsy(self):
        """Test coercion of falsy strings."""
        assert _coerce_to_boolean("") is False

    def test_coerce_none(self):
        """Test coercion of None."""
        assert _coerce_to_boolean(None) is False

    def test_coerce_numpy_array(self):
        """Test coercion of numpy arrays."""
        arr = np.array([1, 0, 2, 0, -1])
        result = _coerce_to_boolean(arr)
        expected = np.array([True, False, True, False, True])
        np.testing.assert_array_equal(result, expected)

    def test_coerce_boolean_array(self):
        """Test handling of boolean arrays."""
        arr = np.array([True, False, True])
        result = _coerce_to_boolean(arr)
        np.testing.assert_array_equal(result, arr)

    def test_coerce_list(self):
        """Test coercion of lists."""
        result = _coerce_to_boolean([1, 0, 2])
        expected = np.array([True, False, True])
        np.testing.assert_array_equal(result, expected)

    def test_coerce_tuple(self):
        """Test coercion of tuples."""
        result = _coerce_to_boolean((1, 0, 2))
        expected = np.array([True, False, True])
        np.testing.assert_array_equal(result, expected)

    def test_coerce_invalid_array(self):
        """Test coercion of non-numeric arrays."""
        arr = np.array(['hello', 'world'])
        with pytest.raises(TypeError, match="Cannot convert array"):
            _coerce_to_boolean(arr)


class TestComparabilityEnsuring:
    """Test cases for ensuring values are comparable."""

    def test_ensure_comparable_same_types(self):
        """Test values that are already the same type."""
        a, b = _ensure_comparable(5, 10)
        assert a == 5 and b == 10
        assert type(a) == type(b)

    def test_ensure_comparable_none_values(self):
        """Test handling of None values."""
        a, b = _ensure_comparable(None, None)
        assert a is None and b is None

        a, b = _ensure_comparable(None, 5)
        assert a is None and b == 5

        a, b = _ensure_comparable(5, None)
        assert a == 5 and b is None

    def test_ensure_comparable_string_conversion(self):
        """Test string conversion for mixed types."""
        a, b = _ensure_comparable("hello", 5)
        assert a == "hello" and b == "5"
        assert isinstance(a, str) and isinstance(b, str)

    def test_ensure_comparable_numeric_conversion(self):
        """Test numeric conversion."""
        a, b = _ensure_comparable(5, 10.0)
        assert isinstance(a, np.ndarray) and isinstance(b, np.ndarray)
        np.testing.assert_equal(a, 5)
        np.testing.assert_equal(b, 10.0)

    def test_ensure_comparable_string_to_numeric(self):
        """Test string to numeric conversion."""
        a, b = _ensure_comparable("5", 10)
        assert isinstance(a, np.ndarray) and isinstance(b, np.ndarray)
        np.testing.assert_equal(a, 5)
        np.testing.assert_equal(b, 10)

        a, b = _ensure_comparable("5.5", 10)
        np.testing.assert_equal(a, 5.5)
        np.testing.assert_equal(b, 10)

    def test_ensure_comparable_arrays(self):
        """Test array comparisons."""
        a, b = _ensure_comparable([1, 2, 3], np.array([4, 5, 6]))
        assert isinstance(a, np.ndarray) and isinstance(b, np.ndarray)
        np.testing.assert_array_equal(a, [1, 2, 3])
        np.testing.assert_array_equal(b, [4, 5, 6])

    def test_ensure_comparable_incompatible_arrays(self):
        """Test incompatible array shapes."""
        with pytest.raises(TypeError, match="not broadcastable"):
            _ensure_comparable([1, 2, 3], [[1, 2], [3, 4], [5, 6]])

    def test_ensure_comparable_fallback_string(self):
        """Test fallback to string comparison."""
        a, b = _ensure_comparable({"a": 1}, [1, 2, 3])
        assert isinstance(a, str) and isinstance(b, str)


class TestAndOperator:
    """Test cases for the AND operator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Operator(
            name="and",
            type=OperatorType.LOGICAL,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["result"]
        )

    def test_initialization(self):
        """Test AND operator initialization."""
        op = AndOperator(self.config)
        assert op.name == "and"
        assert op.logical_config.short_circuit is True

    def test_scalar_and_true(self):
        """Test scalar AND with True values."""
        op = AndOperator(self.config)
        result = op.evaluate(True, True)
        assert result is True

    def test_scalar_and_false(self):
        """Test scalar AND with False values."""
        op = AndOperator(self.config)
        result = op.evaluate(True, False)
        assert result is False

        result = op.evaluate(False, True)
        assert result is False

        result = op.evaluate(False, False)
        assert result is False

    def test_multiple_operand_and(self):
        """Test AND with multiple operands."""
        op = AndOperator(self.config)
        result = op.evaluate(True, True, True)
        assert result is True

        result = op.evaluate(True, False, True)
        assert result is False

    def test_array_and(self):
        """Test AND with arrays."""
        op = AndOperator(self.config)
        a = np.array([True, False, True])
        b = np.array([True, True, False])
        result = op.evaluate(a, b)
        expected = np.array([True, False, False])
        np.testing.assert_array_equal(result, expected)

    def test_broadcasting_and(self):
        """Test AND with broadcasting."""
        op = AndOperator(self.config)
        a = np.array([True, False])
        b = True
        result = op.evaluate(a, b)
        expected = np.array([True, False])
        np.testing.assert_array_equal(result, expected)

    def test_type_coercion_and(self):
        """Test AND with type coercion."""
        op = AndOperator(self.config)
        result = op.evaluate(1, 0)
        assert result is False

        result = op.evaluate(1, 2)
        assert result is True

    def test_insufficient_operands_error(self):
        """Test error with insufficient operands."""
        op = AndOperator(self.config)
        with pytest.raises(ValueError, match="AND requires at least 2 operands"):
            op.evaluate(True)

    def test_strict_type_mode(self):
        """Test strict type mode."""
        config = Operator(
            name="and",
            type=OperatorType.LOGICAL,
            parameters={"strict_types": True},
            input_variables=["a", "b"],
            output_variables=["result"]
        )
        op = AndOperator(config)

        # Should work with boolean types
        result = op.evaluate(True, False)
        assert result is False

        # Should fail with non-boolean types
        with pytest.raises(TypeError, match="Strict mode"):
            op.evaluate(1, 0)


class TestOrOperator:
    """Test cases for the OR operator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Operator(
            name="or",
            type=OperatorType.LOGICAL,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["result"]
        )

    def test_scalar_or_true(self):
        """Test scalar OR with True values."""
        op = OrOperator(self.config)
        result = op.evaluate(True, True)
        assert result is True

        result = op.evaluate(True, False)
        assert result is True

        result = op.evaluate(False, True)
        assert result is True

    def test_scalar_or_false(self):
        """Test scalar OR with False values."""
        op = OrOperator(self.config)
        result = op.evaluate(False, False)
        assert result is False

    def test_multiple_operand_or(self):
        """Test OR with multiple operands."""
        op = OrOperator(self.config)
        result = op.evaluate(False, False, True)
        assert result is True

        result = op.evaluate(False, False, False)
        assert result is False

    def test_array_or(self):
        """Test OR with arrays."""
        op = OrOperator(self.config)
        a = np.array([True, False, True])
        b = np.array([False, False, False])
        result = op.evaluate(a, b)
        expected = np.array([True, False, True])
        np.testing.assert_array_equal(result, expected)


class TestNotOperator:
    """Test cases for the NOT operator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Operator(
            name="not",
            type=OperatorType.LOGICAL,
            parameters={},
            input_variables=["a"],
            output_variables=["result"]
        )

    def test_scalar_not(self):
        """Test scalar NOT operation."""
        op = NotOperator(self.config)
        assert op.evaluate(True) is False
        assert op.evaluate(False) is True

    def test_array_not(self):
        """Test NOT with arrays."""
        op = NotOperator(self.config)
        a = np.array([True, False, True])
        result = op.evaluate(a)
        expected = np.array([False, True, False])
        np.testing.assert_array_equal(result, expected)

    def test_type_coercion_not(self):
        """Test NOT with type coercion."""
        op = NotOperator(self.config)
        assert op.evaluate(1) is False
        assert op.evaluate(0) is True
        assert op.evaluate("hello") is False
        assert op.evaluate("") is True

    def test_wrong_operand_count(self):
        """Test error with wrong number of operands."""
        op = NotOperator(self.config)
        with pytest.raises(ValueError, match="NOT requires exactly 1 operand"):
            op.evaluate(True, False)


class TestComparisonOperators:
    """Test cases for comparison operators."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Operator(
            name="eq",
            type=OperatorType.LOGICAL,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["result"]
        )

    def test_equal_operator(self):
        """Test equality operator."""
        op = EqualOperator(self.config)
        assert op.evaluate(5, 5) is True
        assert op.evaluate(5, 10) is False
        assert op.evaluate("hello", "hello") is True
        assert op.evaluate("hello", "world") is False

    def test_equal_operator_arrays(self):
        """Test equality with arrays."""
        op = EqualOperator(self.config)
        a = np.array([1, 2, 3])
        b = np.array([1, 2, 3])
        result = op.evaluate(a, b)
        expected = np.array([True, True, True])
        np.testing.assert_array_equal(result, expected)

    def test_equal_operator_none(self):
        """Test equality with None values."""
        op = EqualOperator(self.config)
        assert op.evaluate(None, None) is True
        assert op.evaluate(None, 5) is False
        assert op.evaluate(5, None) is False

    def test_not_equal_operator(self):
        """Test not-equal operator."""
        config = Operator(
            name="ne",
            type=OperatorType.LOGICAL,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["result"]
        )
        op = NotEqualOperator(config)
        assert op.evaluate(5, 10) is True
        assert op.evaluate(5, 5) is False

    def test_less_than_operator(self):
        """Test less-than operator."""
        config = Operator(
            name="lt",
            type=OperatorType.LOGICAL,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["result"]
        )
        op = LessThanOperator(config)
        assert op.evaluate(5, 10) is True
        assert op.evaluate(10, 5) is False
        assert op.evaluate(5, 5) is False

    def test_less_than_operator_none(self):
        """Test less-than with None values."""
        config = Operator(
            name="lt",
            type=OperatorType.LOGICAL,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["result"]
        )
        op = LessThanOperator(config)
        assert op.evaluate(None, 5) is True
        assert op.evaluate(5, None) is False
        assert op.evaluate(None, None) is False

    def test_less_than_or_equal_operator(self):
        """Test less-than-or-equal operator."""
        config = Operator(
            name="le",
            type=OperatorType.LOGICAL,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["result"]
        )
        op = LessThanOrEqualOperator(config)
        assert op.evaluate(5, 10) is True
        assert op.evaluate(5, 5) is True
        assert op.evaluate(10, 5) is False

    def test_greater_than_operator(self):
        """Test greater-than operator."""
        config = Operator(
            name="gt",
            type=OperatorType.LOGICAL,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["result"]
        )
        op = GreaterThanOperator(config)
        assert op.evaluate(10, 5) is True
        assert op.evaluate(5, 10) is False
        assert op.evaluate(5, 5) is False

    def test_greater_than_or_equal_operator(self):
        """Test greater-than-or-equal operator."""
        config = Operator(
            name="ge",
            type=OperatorType.LOGICAL,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["result"]
        )
        op = GreaterThanOrEqualOperator(config)
        assert op.evaluate(10, 5) is True
        assert op.evaluate(5, 5) is True
        assert op.evaluate(5, 10) is False

    def test_comparison_with_arrays(self):
        """Test comparison operators with arrays."""
        config = Operator(
            name="lt",
            type=OperatorType.LOGICAL,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["result"]
        )
        op = LessThanOperator(config)
        a = np.array([1, 5, 3])
        b = np.array([2, 4, 3])
        result = op.evaluate(a, b)
        expected = np.array([True, False, False])
        np.testing.assert_array_equal(result, expected)

    def test_comparison_type_coercion(self):
        """Test comparison with type coercion."""
        config = Operator(
            name="eq",
            type=OperatorType.LOGICAL,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["result"]
        )
        op = EqualOperator(config)

        # String to number conversion
        result = op.evaluate("5", 5)
        assert isinstance(result, np.bool_)
        assert result == True

    def test_comparison_wrong_operand_count(self):
        """Test error with wrong number of operands."""
        op = EqualOperator(self.config)
        with pytest.raises(ValueError, match="requires exactly 2 operands"):
            op.evaluate(5)


class TestOperatorRegistry:
    """Test cases for logical operator registry integration."""

    def test_logical_operators_registered(self):
        """Test that logical operators are registered."""
        registry = get_registry()

        logical_operators = registry.list_operators_by_type(OperatorType.LOGICAL)
        expected_operators = ["and", "or", "not", "eq", "ne", "lt", "le", "gt", "ge"]

        for op_name in expected_operators:
            assert op_name in logical_operators

    def test_operator_creation_from_registry(self):
        """Test creating logical operators from registry."""
        registry = get_registry()

        # Test creating AND operator
        and_op = registry.create_operator_by_name(
            "and",
            OperatorType.LOGICAL,
            input_variables=["a", "b"],
            output_variables=["result"]
        )
        assert isinstance(and_op, AndOperator)

        # Test it works
        result = and_op.evaluate(True, False)
        assert result is False

    def test_list_logical_operators(self):
        """Test listing logical operators."""
        registry = get_registry()
        logical_ops = registry.list_operators_by_type(OperatorType.LOGICAL)

        # Should have all logical and comparison operators
        assert len(logical_ops) >= 9
        assert "and" in logical_ops
        assert "or" in logical_ops
        assert "not" in logical_ops
        assert "eq" in logical_ops


class TestLogicalOperatorConfig:
    """Test cases for logical operator configuration."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = LogicalOperatorConfig()
        assert config.short_circuit is True
        assert config.strict_types is False
        assert config.nan_handling == "propagate"

    def test_custom_configuration(self):
        """Test custom configuration through operator parameters."""
        config = Operator(
            name="and",
            type=OperatorType.LOGICAL,
            parameters={
                "short_circuit": False,
                "strict_types": True,
                "nan_handling": "warn"
            },
            input_variables=["a", "b"],
            output_variables=["result"]
        )

        op = AndOperator(config)
        assert op.logical_config.short_circuit is False
        assert op.logical_config.strict_types is True
        assert op.logical_config.nan_handling == "warn"

    def test_short_circuit_disabled(self):
        """Test behavior with short-circuit evaluation disabled."""
        config = Operator(
            name="and",
            type=OperatorType.LOGICAL,
            parameters={"short_circuit": False},
            input_variables=["a", "b", "c"],
            output_variables=["result"]
        )

        op = AndOperator(config)

        # Even with short-circuit disabled, result should be the same
        result = op.evaluate(False, True, True)
        assert result is False


class TestEdgeCases:
    """Test cases for edge cases and error conditions."""

    def test_mixed_scalar_array_operations(self):
        """Test operations mixing scalars and arrays."""
        config = Operator(
            name="and",
            type=OperatorType.LOGICAL,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["result"]
        )

        op = AndOperator(config)

        # Scalar with array
        result = op.evaluate(True, np.array([True, False, True]))
        expected = np.array([True, False, True])
        np.testing.assert_array_equal(result, expected)

        # Array with scalar
        result = op.evaluate(np.array([True, False, True]), False)
        expected = np.array([False, False, False])
        np.testing.assert_array_equal(result, expected)

    def test_complex_type_coercion(self):
        """Test complex type coercion scenarios."""
        config = Operator(
            name="eq",
            type=OperatorType.LOGICAL,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["result"]
        )

        op = EqualOperator(config)

        # Mixed numeric types
        result = op.evaluate(5, 5.0)
        assert result == True

        # String and number (should convert to numeric)
        result = op.evaluate("5", 5)
        assert result == True

        # List and array
        result = op.evaluate([1, 2, 3], np.array([1, 2, 3]))
        expected = np.array([True, True, True])
        np.testing.assert_array_equal(result, expected)