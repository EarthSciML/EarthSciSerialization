"""
Tests for statistical operators in ESM Format.

This module tests the statistical operator implementations including
mean, variance, standard deviation, percentile, and median operations.
"""

import pytest
import numpy as np
import warnings
from unittest.mock import patch

from src.esm_format.statistical_operators import (
    MeanOperator, VarianceOperator, StandardDeviationOperator,
    PercentileOperator, MedianOperator, _ensure_numeric_array, _validate_axis
)
from src.esm_format.types import Operator, OperatorType
from src.esm_format.operator_registry import get_registry


class TestStatisticalOperatorUtilities:
    """Test utility functions for statistical operators."""

    def test_ensure_numeric_array_with_array(self):
        """Test _ensure_numeric_array with numpy array input."""
        arr = np.array([1, 2, 3, 4, 5])
        result = _ensure_numeric_array(arr)
        np.testing.assert_array_equal(result, arr)

    def test_ensure_numeric_array_with_list(self):
        """Test _ensure_numeric_array with list input."""
        data = [1, 2, 3, 4, 5]
        result = _ensure_numeric_array(data)
        expected = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        np.testing.assert_array_equal(result, expected)

    def test_ensure_numeric_array_with_scalar(self):
        """Test _ensure_numeric_array with scalar input."""
        result = _ensure_numeric_array(42)
        expected = np.array([42])
        np.testing.assert_array_equal(result, expected)

    def test_ensure_numeric_array_with_string_number(self):
        """Test _ensure_numeric_array with string number."""
        result = _ensure_numeric_array("3.14")
        expected = np.array([3.14])
        np.testing.assert_array_almost_equal(result, expected)

    def test_ensure_numeric_array_invalid_string(self):
        """Test _ensure_numeric_array with invalid string."""
        with pytest.raises(TypeError, match="Cannot convert string"):
            _ensure_numeric_array("not_a_number")

    def test_ensure_numeric_array_non_numeric_array(self):
        """Test _ensure_numeric_array with non-numeric array."""
        arr = np.array(['a', 'b', 'c'])
        with pytest.raises(TypeError, match="Array must contain numeric values"):
            _ensure_numeric_array(arr)

    def test_validate_axis_none(self):
        """Test _validate_axis with None."""
        result = _validate_axis(None, 3)
        assert result is None

    def test_validate_axis_positive_integer(self):
        """Test _validate_axis with positive integer."""
        result = _validate_axis(1, 3)
        assert result == 1

    def test_validate_axis_negative_integer(self):
        """Test _validate_axis with negative integer."""
        result = _validate_axis(-1, 3)
        assert result == 2

    def test_validate_axis_tuple(self):
        """Test _validate_axis with tuple."""
        result = _validate_axis((0, 2), 3)
        assert result == (0, 2)

    def test_validate_axis_out_of_bounds(self):
        """Test _validate_axis with out of bounds axis."""
        with pytest.raises(ValueError, match="out of bounds"):
            _validate_axis(5, 3)

    def test_validate_axis_invalid_type(self):
        """Test _validate_axis with invalid type."""
        with pytest.raises(ValueError, match="must be int"):
            _validate_axis("invalid", 3)


class TestMeanOperator:
    """Test mean operator functionality."""

    def test_mean_operator_initialization(self):
        """Test MeanOperator initialization."""
        config = Operator(
            name="mean",
            type=OperatorType.STATISTICAL,
            parameters={"nan_handling": "warn"}
        )
        op = MeanOperator(config)
        assert op.name == "mean"
        assert op.stat_config.nan_handling == "warn"

    def test_mean_operator_simple_array(self):
        """Test mean calculation with simple array."""
        config = Operator(name="mean", type=OperatorType.STATISTICAL)
        op = MeanOperator(config)

        data = np.array([1, 2, 3, 4, 5])
        result = op.evaluate(data)
        expected = np.mean(data)

        assert result == expected

    def test_mean_operator_with_axis(self):
        """Test mean calculation with axis parameter."""
        config = Operator(
            name="mean",
            type=OperatorType.STATISTICAL,
            parameters={"axis": 0}
        )
        op = MeanOperator(config)

        data = np.array([[1, 2, 3], [4, 5, 6]])
        result = op.evaluate(data)
        expected = np.mean(data, axis=0)

        np.testing.assert_array_equal(result, expected)

    def test_mean_operator_with_nan_omit(self):
        """Test mean calculation with NaN omission."""
        config = Operator(
            name="mean",
            type=OperatorType.STATISTICAL,
            parameters={"nan_handling": "omit"}
        )
        op = MeanOperator(config)

        data = np.array([1, 2, np.nan, 4, 5])
        result = op.evaluate(data)
        expected = np.nanmean(data)

        assert result == expected

    def test_mean_operator_with_nan_warn(self):
        """Test mean calculation with NaN warning."""
        config = Operator(
            name="mean",
            type=OperatorType.STATISTICAL,
            parameters={"nan_handling": "warn"}
        )
        op = MeanOperator(config)

        data = np.array([1, 2, np.nan, 4, 5])

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = op.evaluate(data)
            assert len(w) >= 1
            assert "NaN values found" in str(w[0].message)

    def test_mean_operator_empty_array(self):
        """Test mean calculation with empty array."""
        config = Operator(name="mean", type=OperatorType.STATISTICAL)
        op = MeanOperator(config)

        with pytest.raises(ValueError, match="Cannot compute statistics on empty array"):
            op.evaluate([])


class TestVarianceOperator:
    """Test variance operator functionality."""

    def test_variance_operator_simple(self):
        """Test variance calculation with simple array."""
        config = Operator(name="variance", type=OperatorType.STATISTICAL)
        op = VarianceOperator(config)

        data = np.array([1, 2, 3, 4, 5])
        result = op.evaluate(data)
        expected = np.var(data)

        assert result == expected

    def test_variance_operator_with_ddof(self):
        """Test variance calculation with ddof parameter."""
        config = Operator(
            name="variance",
            type=OperatorType.STATISTICAL,
            parameters={"ddof": 1}
        )
        op = VarianceOperator(config)

        data = np.array([1, 2, 3, 4, 5])
        result = op.evaluate(data)
        expected = np.var(data, ddof=1)

        assert result == expected

    def test_variance_operator_2d_with_axis(self):
        """Test variance calculation on 2D array with axis."""
        config = Operator(
            name="variance",
            type=OperatorType.STATISTICAL,
            parameters={"axis": 1, "keepdims": True}
        )
        op = VarianceOperator(config)

        data = np.array([[1, 2, 3], [4, 5, 6]])
        result = op.evaluate(data)
        expected = np.var(data, axis=1, keepdims=True)

        np.testing.assert_array_equal(result, expected)


class TestStandardDeviationOperator:
    """Test standard deviation operator functionality."""

    def test_std_operator_simple(self):
        """Test standard deviation calculation with simple array."""
        config = Operator(name="std", type=OperatorType.STATISTICAL)
        op = StandardDeviationOperator(config)

        data = np.array([1, 2, 3, 4, 5])
        result = op.evaluate(data)
        expected = np.std(data)

        assert result == expected

    def test_std_operator_consistency_with_variance(self):
        """Test that std is sqrt of variance."""
        config = Operator(
            name="std",
            type=OperatorType.STATISTICAL,
            parameters={"ddof": 1}
        )
        std_op = StandardDeviationOperator(config)

        var_config = Operator(
            name="variance",
            type=OperatorType.STATISTICAL,
            parameters={"ddof": 1}
        )
        var_op = VarianceOperator(var_config)

        data = np.array([1, 2, 3, 4, 5])
        std_result = std_op.evaluate(data)
        var_result = var_op.evaluate(data)

        np.testing.assert_almost_equal(std_result, np.sqrt(var_result))


class TestPercentileOperator:
    """Test percentile operator functionality."""

    def test_percentile_operator_median(self):
        """Test percentile calculation for median (50th percentile)."""
        config = Operator(name="percentile", type=OperatorType.STATISTICAL)
        op = PercentileOperator(config)

        data = np.array([1, 2, 3, 4, 5])
        result = op.evaluate(data, 50)
        expected = np.percentile(data, 50)

        assert result == expected

    def test_percentile_operator_multiple_percentiles(self):
        """Test percentile calculation with multiple percentiles."""
        config = Operator(name="percentile", type=OperatorType.STATISTICAL)
        op = PercentileOperator(config)

        data = np.array([1, 2, 3, 4, 5])
        percentiles = [25, 50, 75]
        result = op.evaluate(data, percentiles)
        expected = np.percentile(data, percentiles)

        np.testing.assert_array_equal(result, expected)

    def test_percentile_operator_from_parameters(self):
        """Test percentile calculation with q from parameters."""
        config = Operator(
            name="percentile",
            type=OperatorType.STATISTICAL,
            parameters={"q": 75}
        )
        op = PercentileOperator(config)

        data = np.array([1, 2, 3, 4, 5])
        result = op.evaluate(data)
        expected = np.percentile(data, 75)

        assert result == expected

    def test_percentile_operator_invalid_q(self):
        """Test percentile calculation with invalid q value."""
        config = Operator(name="percentile", type=OperatorType.STATISTICAL)
        op = PercentileOperator(config)

        data = np.array([1, 2, 3, 4, 5])
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            op.evaluate(data, 150)

    def test_percentile_operator_interpolation_method(self):
        """Test percentile calculation with different interpolation methods."""
        config = Operator(
            name="percentile",
            type=OperatorType.STATISTICAL,
            parameters={"interpolation": "lower"}
        )
        op = PercentileOperator(config)

        data = np.array([1, 2, 3, 4])
        result = op.evaluate(data, 50)
        expected = np.percentile(data, 50, method="lower")

        assert result == expected


class TestMedianOperator:
    """Test median operator functionality."""

    def test_median_operator_simple(self):
        """Test median calculation with simple array."""
        config = Operator(name="median", type=OperatorType.STATISTICAL)
        op = MedianOperator(config)

        data = np.array([1, 2, 3, 4, 5])
        result = op.evaluate(data)
        expected = np.median(data)

        assert result == expected

    def test_median_operator_even_length(self):
        """Test median calculation with even-length array."""
        config = Operator(name="median", type=OperatorType.STATISTICAL)
        op = MedianOperator(config)

        data = np.array([1, 2, 3, 4])
        result = op.evaluate(data)
        expected = np.median(data)

        assert result == expected

    def test_median_operator_with_axis(self):
        """Test median calculation with axis parameter."""
        config = Operator(
            name="median",
            type=OperatorType.STATISTICAL,
            parameters={"axis": 1}
        )
        op = MedianOperator(config)

        data = np.array([[1, 2, 3], [4, 5, 6]])
        result = op.evaluate(data)
        expected = np.median(data, axis=1)

        np.testing.assert_array_equal(result, expected)


class TestOperatorRegistryIntegration:
    """Test integration with the operator registry."""

    def test_statistical_operators_registered(self):
        """Test that all statistical operators are registered."""
        registry = get_registry()
        statistical_ops = registry.list_operators_by_type(OperatorType.STATISTICAL)

        expected_ops = ["mean", "variance", "std", "percentile", "median"]
        for op in expected_ops:
            assert op in statistical_ops

    def test_create_statistical_operators_via_registry(self):
        """Test creating statistical operators through the registry."""
        registry = get_registry()

        # Test creating each statistical operator
        mean_op = registry.create_operator_by_name("mean", OperatorType.STATISTICAL)
        assert isinstance(mean_op, MeanOperator)

        var_op = registry.create_operator_by_name("variance", OperatorType.STATISTICAL)
        assert isinstance(var_op, VarianceOperator)

        std_op = registry.create_operator_by_name("std", OperatorType.STATISTICAL)
        assert isinstance(std_op, StandardDeviationOperator)

        percentile_op = registry.create_operator_by_name("percentile", OperatorType.STATISTICAL)
        assert isinstance(percentile_op, PercentileOperator)

        median_op = registry.create_operator_by_name("median", OperatorType.STATISTICAL)
        assert isinstance(median_op, MedianOperator)

    def test_statistical_operators_precedence(self):
        """Test precedence settings for statistical operators."""
        registry = get_registry()

        statistical_ops = ["mean", "variance", "std", "percentile", "median"]
        for op_name in statistical_ops:
            precedence = registry.get_operator_precedence(op_name)
            assert precedence is not None
            assert precedence.level == 1  # Same as functions

    def test_end_to_end_statistical_calculation(self):
        """Test end-to-end statistical calculation through registry."""
        registry = get_registry()

        # Create test data
        data = np.random.rand(100)

        # Test mean
        mean_op = registry.create_operator_by_name("mean", OperatorType.STATISTICAL)
        mean_result = mean_op.evaluate(data)
        np.testing.assert_almost_equal(mean_result, np.mean(data))

        # Test variance
        var_op = registry.create_operator_by_name("variance", OperatorType.STATISTICAL)
        var_result = var_op.evaluate(data)
        np.testing.assert_almost_equal(var_result, np.var(data))

        # Test standard deviation
        std_op = registry.create_operator_by_name("std", OperatorType.STATISTICAL)
        std_result = std_op.evaluate(data)
        np.testing.assert_almost_equal(std_result, np.std(data))


class TestErrorHandling:
    """Test error handling in statistical operators."""

    def test_mean_operator_with_invalid_input(self):
        """Test mean operator with invalid input."""
        config = Operator(name="mean", type=OperatorType.STATISTICAL)
        op = MeanOperator(config)

        with pytest.raises(TypeError):
            op.evaluate("invalid_input")

    def test_nan_handling_raise_option(self):
        """Test NaN handling with raise option."""
        config = Operator(
            name="mean",
            type=OperatorType.STATISTICAL,
            parameters={"nan_handling": "raise"}
        )
        op = MeanOperator(config)

        data = np.array([1, 2, np.nan, 4, 5])
        with pytest.raises(ValueError, match="NaN values found"):
            op.evaluate(data)

    def test_invalid_axis_parameter(self):
        """Test operators with invalid axis parameters."""
        config = Operator(
            name="mean",
            type=OperatorType.STATISTICAL,
            parameters={"axis": 10}  # Out of bounds
        )
        op = MeanOperator(config)

        data = np.array([1, 2, 3, 4, 5])  # 1D array
        with pytest.raises(ValueError, match="out of bounds"):
            op.evaluate(data)


if __name__ == "__main__":
    pytest.main([__file__])