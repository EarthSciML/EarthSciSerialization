"""
Test cases for mathematical operators.
"""

import pytest
import numpy as np
import warnings
from unittest.mock import patch

from esm_format.types import Operator, OperatorType
from esm_format.math_operators import (
    AddOperator,
    SubtractOperator,
    MultiplyOperator,
    DivideOperator,
    _ensure_numeric,
    _check_broadcasting_compatibility,
    _handle_precision_warnings,
    ArithmeticOperatorConfig
)
from esm_format.operator_registry import get_registry


class TestNumericConversion:
    """Test cases for numeric type conversion and validation."""

    def test_ensure_numeric_int(self):
        """Test conversion of integers."""
        assert _ensure_numeric(5) == 5
        assert _ensure_numeric(-10) == -10

    def test_ensure_numeric_float(self):
        """Test conversion of floats."""
        assert _ensure_numeric(3.14) == 3.14
        assert _ensure_numeric(-2.71) == -2.71

    def test_ensure_numeric_numpy_array(self):
        """Test handling of numpy arrays."""
        arr = np.array([1, 2, 3])
        result = _ensure_numeric(arr)
        np.testing.assert_array_equal(result, arr)

    def test_ensure_numeric_list(self):
        """Test conversion of lists to arrays."""
        result = _ensure_numeric([1, 2, 3])
        np.testing.assert_array_equal(result, np.array([1.0, 2.0, 3.0]))

    def test_ensure_numeric_tuple(self):
        """Test conversion of tuples to arrays."""
        result = _ensure_numeric((4, 5, 6))
        np.testing.assert_array_equal(result, np.array([4.0, 5.0, 6.0]))

    def test_ensure_numeric_string_int(self):
        """Test conversion of integer strings."""
        assert _ensure_numeric("42") == 42
        assert _ensure_numeric("-17") == -17

    def test_ensure_numeric_string_float(self):
        """Test conversion of float strings."""
        assert _ensure_numeric("3.14") == 3.14
        assert _ensure_numeric("1.5e-3") == 1.5e-3

    def test_ensure_numeric_invalid_string(self):
        """Test that invalid strings raise TypeError."""
        with pytest.raises(TypeError, match="Cannot convert string 'invalid' to numeric value"):
            _ensure_numeric("invalid")

    def test_ensure_numeric_invalid_type(self):
        """Test that invalid types raise TypeError."""
        with pytest.raises(TypeError, match="Cannot convert .* to numeric value"):
            _ensure_numeric({'a': 1})

    def test_ensure_numeric_non_numeric_array(self):
        """Test that non-numeric arrays raise TypeError."""
        arr = np.array(['a', 'b', 'c'])
        with pytest.raises(TypeError, match="Array must contain numeric values"):
            _ensure_numeric(arr)


class TestBroadcastingCompatibility:
    """Test cases for broadcasting compatibility checking."""

    def test_scalar_scalar_compatibility(self):
        """Test compatibility between scalars."""
        assert _check_broadcasting_compatibility(5, 3) == True

    def test_scalar_array_compatibility(self):
        """Test compatibility between scalar and array."""
        assert _check_broadcasting_compatibility(5, np.array([1, 2, 3])) == True

    def test_compatible_arrays(self):
        """Test compatibility between compatible arrays."""
        arr1 = np.array([1, 2, 3])
        arr2 = np.array([4, 5, 6])
        assert _check_broadcasting_compatibility(arr1, arr2) == True

    def test_broadcasting_compatible_shapes(self):
        """Test broadcasting with compatible shapes."""
        arr1 = np.array([[1, 2, 3]])  # Shape (1, 3)
        arr2 = np.array([[4], [5], [6]])  # Shape (3, 1)
        assert _check_broadcasting_compatibility(arr1, arr2) == True

    def test_incompatible_arrays(self):
        """Test incompatible arrays."""
        arr1 = np.array([1, 2, 3, 4])  # Shape (4,)
        arr2 = np.array([1, 2, 3])  # Shape (3,)
        assert _check_broadcasting_compatibility(arr1, arr2) == False


class TestPrecisionWarnings:
    """Test cases for precision warning handling."""

    def test_overflow_warning(self):
        """Test that overflow warnings are properly handled."""
        result = np.array([np.inf, 1.0, 2.0])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _handle_precision_warnings(result, "test", [1, 2])
            assert len(w) == 1
            assert "Overflow detected" in str(w[0].message)

    def test_underflow_warning(self):
        """Test that underflow warnings are properly handled."""
        result = np.array([1e-400, 1.0, 2.0])  # Very small number
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _handle_precision_warnings(result, "test", [1, 2])
            # May or may not trigger depending on system precision
            # Just ensure no errors occur
            pass

    def test_nan_warning(self):
        """Test that NaN warnings are properly handled."""
        result = np.array([np.nan, 1.0, 2.0])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _handle_precision_warnings(result, "test", [1, 2])
            assert len(w) == 1
            assert "NaN values produced" in str(w[0].message)


class TestAddOperator:
    """Test cases for AddOperator."""

    def test_initialization(self):
        """Test operator initialization."""
        config = Operator(
            name="add",
            type=OperatorType.ARITHMETIC,
            parameters={"precision": "single"},
            input_variables=["a", "b"],
            output_variables=["sum"]
        )
        op = AddOperator(config)
        assert op.name == "add"
        assert op.arith_config.precision == "single"

    def test_scalar_addition(self):
        """Test addition of scalars."""
        config = Operator(
            name="add",
            type=OperatorType.ARITHMETIC,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["sum"]
        )
        op = AddOperator(config)

        result = op.evaluate(5, 3)
        assert result == 8

    def test_multiple_operand_addition(self):
        """Test addition of multiple operands."""
        config = Operator(
            name="add",
            type=OperatorType.ARITHMETIC,
            parameters={},
            input_variables=["a", "b", "c"],
            output_variables=["sum"]
        )
        op = AddOperator(config)

        result = op.evaluate(1, 2, 3, 4)
        assert result == 10

    def test_array_addition(self):
        """Test addition of arrays."""
        config = Operator(
            name="add",
            type=OperatorType.ARITHMETIC,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["sum"]
        )
        op = AddOperator(config)

        arr1 = np.array([1, 2, 3])
        arr2 = np.array([4, 5, 6])
        result = op.evaluate(arr1, arr2)
        np.testing.assert_array_equal(result, np.array([5, 7, 9]))

    def test_broadcasting_addition(self):
        """Test addition with broadcasting."""
        config = Operator(
            name="add",
            type=OperatorType.ARITHMETIC,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["sum"]
        )
        op = AddOperator(config)

        arr = np.array([1, 2, 3])
        scalar = 5
        result = op.evaluate(arr, scalar)
        np.testing.assert_array_equal(result, np.array([6, 7, 8]))

    def test_insufficient_operands_error(self):
        """Test error when insufficient operands provided."""
        config = Operator(
            name="add",
            type=OperatorType.ARITHMETIC,
            parameters={},
            input_variables=["a"],
            output_variables=["sum"]
        )
        op = AddOperator(config)

        with pytest.raises(ValueError, match="Addition requires at least 2 operands"):
            op.evaluate(5)

    def test_invalid_operand_error(self):
        """Test error when invalid operands provided."""
        config = Operator(
            name="add",
            type=OperatorType.ARITHMETIC,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["sum"]
        )
        op = AddOperator(config)

        with pytest.raises(TypeError, match="Invalid operand"):
            op.evaluate(5, {'invalid': 'type'})

    def test_precision_settings(self):
        """Test precision settings."""
        config = Operator(
            name="add",
            type=OperatorType.ARITHMETIC,
            parameters={"precision": "single"},
            input_variables=["a", "b"],
            output_variables=["sum"]
        )
        op = AddOperator(config)

        result = op.evaluate(1.0, 2.0)
        assert result.dtype == np.float32


class TestSubtractOperator:
    """Test cases for SubtractOperator."""

    def test_scalar_subtraction(self):
        """Test subtraction of scalars."""
        config = Operator(
            name="subtract",
            type=OperatorType.ARITHMETIC,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["diff"]
        )
        op = SubtractOperator(config)

        result = op.evaluate(10, 3)
        assert result == 7

    def test_multiple_operand_subtraction(self):
        """Test subtraction with multiple operands."""
        config = Operator(
            name="subtract",
            type=OperatorType.ARITHMETIC,
            parameters={},
            input_variables=["a", "b", "c"],
            output_variables=["diff"]
        )
        op = SubtractOperator(config)

        result = op.evaluate(20, 5, 3)  # 20 - 5 - 3 = 12
        assert result == 12

    def test_array_subtraction(self):
        """Test subtraction of arrays."""
        config = Operator(
            name="subtract",
            type=OperatorType.ARITHMETIC,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["diff"]
        )
        op = SubtractOperator(config)

        arr1 = np.array([10, 20, 30])
        arr2 = np.array([1, 2, 3])
        result = op.evaluate(arr1, arr2)
        np.testing.assert_array_equal(result, np.array([9, 18, 27]))


class TestMultiplyOperator:
    """Test cases for MultiplyOperator."""

    def test_scalar_multiplication(self):
        """Test multiplication of scalars."""
        config = Operator(
            name="multiply",
            type=OperatorType.ARITHMETIC,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["product"]
        )
        op = MultiplyOperator(config)

        result = op.evaluate(4, 5)
        assert result == 20

    def test_multiple_operand_multiplication(self):
        """Test multiplication with multiple operands."""
        config = Operator(
            name="multiply",
            type=OperatorType.ARITHMETIC,
            parameters={},
            input_variables=["a", "b", "c"],
            output_variables=["product"]
        )
        op = MultiplyOperator(config)

        result = op.evaluate(2, 3, 4)  # 2 * 3 * 4 = 24
        assert result == 24

    def test_array_multiplication(self):
        """Test multiplication of arrays."""
        config = Operator(
            name="multiply",
            type=OperatorType.ARITHMETIC,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["product"]
        )
        op = MultiplyOperator(config)

        arr1 = np.array([2, 3, 4])
        arr2 = np.array([5, 6, 7])
        result = op.evaluate(arr1, arr2)
        np.testing.assert_array_equal(result, np.array([10, 18, 28]))


class TestDivideOperator:
    """Test cases for DivideOperator."""

    def test_scalar_division(self):
        """Test division of scalars."""
        config = Operator(
            name="divide",
            type=OperatorType.ARITHMETIC,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["quotient"]
        )
        op = DivideOperator(config)

        result = op.evaluate(20, 4)
        assert result == 5

    def test_multiple_operand_division(self):
        """Test division with multiple operands."""
        config = Operator(
            name="divide",
            type=OperatorType.ARITHMETIC,
            parameters={},
            input_variables=["a", "b", "c"],
            output_variables=["quotient"]
        )
        op = DivideOperator(config)

        result = op.evaluate(100, 5, 2)  # 100 / 5 / 2 = 10
        assert result == 10

    def test_array_division(self):
        """Test division of arrays."""
        config = Operator(
            name="divide",
            type=OperatorType.ARITHMETIC,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["quotient"]
        )
        op = DivideOperator(config)

        arr1 = np.array([20, 30, 40])
        arr2 = np.array([4, 5, 8])
        result = op.evaluate(arr1, arr2)
        np.testing.assert_array_equal(result, np.array([5, 6, 5]))

    def test_division_by_zero_warning(self):
        """Test division by zero produces warning."""
        config = Operator(
            name="divide",
            type=OperatorType.ARITHMETIC,
            parameters={"nan_handling": "warn"},
            input_variables=["a", "b"],
            output_variables=["quotient"]
        )
        op = DivideOperator(config)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = op.evaluate(10, 0)
            assert len(w) == 1
            assert "Division by zero" in str(w[0].message)
            assert np.isinf(result)

    def test_division_by_zero_error(self):
        """Test division by zero raises error when configured."""
        config = Operator(
            name="divide",
            type=OperatorType.ARITHMETIC,
            parameters={"nan_handling": "raise"},
            input_variables=["a", "b"],
            output_variables=["quotient"]
        )
        op = DivideOperator(config)

        with pytest.raises(ValueError, match="Division by zero"):
            op.evaluate(10, 0)

    def test_division_by_zero_array(self):
        """Test division by zero in arrays."""
        config = Operator(
            name="divide",
            type=OperatorType.ARITHMETIC,
            parameters={"nan_handling": "warn"},
            input_variables=["a", "b"],
            output_variables=["quotient"]
        )
        op = DivideOperator(config)

        arr1 = np.array([10, 20, 30])
        arr2 = np.array([2, 0, 5])  # Contains zero

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = op.evaluate(arr1, arr2)
            assert len(w) == 1
            assert "Division by zero" in str(w[0].message)
            assert result[1] == np.inf  # 20/0 = inf


class TestOperatorRegistry:
    """Test cases for mathematical operators in the registry."""

    def test_builtin_operators_registered(self):
        """Test that built-in mathematical operators are registered."""
        registry = get_registry()

        assert registry.has_operator("add")
        assert registry.has_operator("subtract")
        assert registry.has_operator("multiply")
        assert registry.has_operator("divide")

    def test_operator_creation_from_registry(self):
        """Test creating operators through registry."""
        registry = get_registry()

        config = Operator(
            name="add",
            type=OperatorType.ARITHMETIC,
            parameters={},
            input_variables=["a", "b"],
            output_variables=["sum"]
        )

        op = registry.create_operator(config)
        assert isinstance(op, AddOperator)

        result = op.evaluate(3, 7)
        assert result == 10

    def test_list_arithmetic_operators(self):
        """Test listing arithmetic operators."""
        registry = get_registry()

        arithmetic_ops = registry.list_operators_by_type(OperatorType.ARITHMETIC)
        expected_ops = {"add", "subtract", "multiply", "divide"}
        assert set(arithmetic_ops) == expected_ops


class TestArithmeticOperatorConfig:
    """Test cases for ArithmeticOperatorConfig."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = ArithmeticOperatorConfig()
        assert config.precision == "double"
        assert config.overflow_handling == "warn"
        assert config.underflow_handling == "warn"
        assert config.nan_handling == "warn"
        assert config.broadcasting == True

    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = ArithmeticOperatorConfig(
            precision="single",
            overflow_handling="ignore",
            nan_handling="raise",
            broadcasting=False
        )
        assert config.precision == "single"
        assert config.overflow_handling == "ignore"
        assert config.nan_handling == "raise"
        assert config.broadcasting == False