"""
Statistical operator implementations for ESM Format.

This module provides implementations for statistical operations including
aggregation functions (mean, variance) and distribution analysis (percentiles).
Important for data processing pipelines and analysis workflows.
"""

import warnings
import numpy as np
from typing import Any, Union, List, Dict, Optional, Tuple
from dataclasses import dataclass

from .esm_types import Operator, OperatorType


def _ensure_numeric_array(value: Any) -> np.ndarray:
    """
    Ensure a value is a numeric numpy array.

    Args:
        value: Input value to convert

    Returns:
        Numeric numpy array

    Raises:
        TypeError: If value cannot be converted to a numeric array
    """
    if isinstance(value, np.ndarray):
        if not np.issubdtype(value.dtype, np.number):
            raise TypeError(f"Array must contain numeric values, got dtype: {value.dtype}")
        return value
    elif isinstance(value, (int, float)):
        return np.array([value])
    elif isinstance(value, (list, tuple)):
        try:
            return np.array(value, dtype=float)
        except (ValueError, TypeError) as e:
            raise TypeError(f"Cannot convert sequence to numeric array: {e}")
    elif isinstance(value, str):
        try:
            # Try to parse as a single number
            num_val = float(value)
            return np.array([num_val])
        except ValueError:
            raise TypeError(f"Cannot convert string '{value}' to numeric value")
    else:
        try:
            return np.asarray(value, dtype=float)
        except (ValueError, TypeError):
            raise TypeError(f"Cannot convert {type(value).__name__} to numeric array")


def _validate_axis(axis: Optional[Union[int, Tuple[int, ...]]], ndim: int) -> Optional[Union[int, Tuple[int, ...]]]:
    """
    Validate axis parameter for statistical operations.

    Args:
        axis: Axis or axes along which to operate
        ndim: Number of dimensions in the array

    Returns:
        Validated axis parameter

    Raises:
        ValueError: If axis is invalid
    """
    if axis is None:
        return None

    if isinstance(axis, int):
        if axis < 0:
            axis = ndim + axis
        if axis < 0 or axis >= ndim:
            raise ValueError(f"Axis {axis} is out of bounds for array with {ndim} dimensions")
        return axis

    if isinstance(axis, (tuple, list)):
        validated = []
        for ax in axis:
            if not isinstance(ax, int):
                raise ValueError(f"Axis values must be integers, got {type(ax).__name__}")
            if ax < 0:
                ax = ndim + ax
            if ax < 0 or ax >= ndim:
                raise ValueError(f"Axis {ax} is out of bounds for array with {ndim} dimensions")
            validated.append(ax)
        return tuple(validated)

    raise ValueError(f"Axis must be int, tuple of ints, or None, got {type(axis).__name__}")


@dataclass
class StatisticalOperatorConfig:
    """Configuration for statistical operators."""
    nan_handling: str = "warn"  # "ignore", "warn", "raise", "omit"
    ddof: int = 0  # Delta degrees of freedom for variance calculations
    keepdims: bool = False  # Keep dimensions after reduction
    interpolation: str = "linear"  # For percentile: "linear", "lower", "higher", "midpoint", "nearest"


class BaseStatisticalOperator:
    """
    Base class for statistical operators.

    Provides common functionality for input validation, axis handling,
    and NaN processing.
    """

    def __init__(self, config: Operator):
        """
        Initialize the statistical operator.

        Args:
            config: Operator configuration
        """
        self.config = config
        self.name = config.name
        self.parameters = config.parameters
        self.input_variables = config.input_variables
        self.output_variables = config.output_variables

        # Parse statistical-specific configuration
        self.stat_config = StatisticalOperatorConfig()
        if "nan_handling" in self.parameters:
            self.stat_config.nan_handling = self.parameters["nan_handling"]
        if "ddof" in self.parameters:
            self.stat_config.ddof = int(self.parameters["ddof"])
        if "keepdims" in self.parameters:
            self.stat_config.keepdims = bool(self.parameters["keepdims"])
        if "interpolation" in self.parameters:
            self.stat_config.interpolation = self.parameters["interpolation"]

    def _validate_input(self, data: Any) -> np.ndarray:
        """
        Validate and convert input data to numpy array.

        Args:
            data: Input data

        Returns:
            Validated numpy array

        Raises:
            TypeError: If input cannot be converted to numeric array
            ValueError: If array is empty or has invalid NaN handling
        """
        array = _ensure_numeric_array(data)

        if array.size == 0:
            raise ValueError("Cannot compute statistics on empty array")

        # Handle NaN values based on configuration
        if np.any(np.isnan(array)):
            if self.stat_config.nan_handling == "raise":
                raise ValueError("NaN values found in input data")
            elif self.stat_config.nan_handling == "warn":
                warnings.warn("NaN values found in input data", RuntimeWarning)

        return array

    def _get_axis_param(self) -> Optional[Union[int, Tuple[int, ...]]]:
        """Get the axis parameter from configuration."""
        if "axis" not in self.parameters:
            return None

        axis = self.parameters["axis"]
        if axis is None:
            return None
        elif isinstance(axis, (int, list, tuple)):
            return axis
        else:
            try:
                return int(axis)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid axis parameter: {axis}")


class MeanOperator(BaseStatisticalOperator):
    """Mean (average) operator for statistical aggregation."""

    def evaluate(self, data: Any) -> Any:
        """
        Compute the arithmetic mean of the input data.

        Args:
            data: Input data array

        Returns:
            Mean value or array

        Raises:
            TypeError: If input cannot be converted to numeric array
            ValueError: If input is empty or has invalid configuration
        """
        array = self._validate_input(data)
        axis = self._get_axis_param()

        if axis is not None:
            axis = _validate_axis(axis, array.ndim)

        try:
            if self.stat_config.nan_handling == "omit":
                result = np.nanmean(array, axis=axis, keepdims=self.stat_config.keepdims)
            else:
                result = np.mean(array, axis=axis, keepdims=self.stat_config.keepdims)

            # Check for warnings
            if np.any(np.isnan(result)) and self.stat_config.nan_handling == "warn":
                warnings.warn("NaN values in mean result", RuntimeWarning)

            return result

        except Exception as e:
            raise ValueError(f"Mean calculation failed: {e}")


class VarianceOperator(BaseStatisticalOperator):
    """Variance operator for statistical analysis."""

    def evaluate(self, data: Any) -> Any:
        """
        Compute the variance of the input data.

        Args:
            data: Input data array

        Returns:
            Variance value or array

        Raises:
            TypeError: If input cannot be converted to numeric array
            ValueError: If input is empty or has invalid configuration
        """
        array = self._validate_input(data)
        axis = self._get_axis_param()

        if axis is not None:
            axis = _validate_axis(axis, array.ndim)

        try:
            if self.stat_config.nan_handling == "omit":
                result = np.nanvar(array, axis=axis, ddof=self.stat_config.ddof, keepdims=self.stat_config.keepdims)
            else:
                result = np.var(array, axis=axis, ddof=self.stat_config.ddof, keepdims=self.stat_config.keepdims)

            # Check for warnings
            if np.any(np.isnan(result)) and self.stat_config.nan_handling == "warn":
                warnings.warn("NaN values in variance result", RuntimeWarning)

            return result

        except Exception as e:
            raise ValueError(f"Variance calculation failed: {e}")


class PercentileOperator(BaseStatisticalOperator):
    """Percentile operator for distribution analysis."""

    def evaluate(self, data: Any, q: Union[float, List[float]] = 50.0) -> Any:
        """
        Compute percentiles of the input data.

        Args:
            data: Input data array
            q: Percentile or sequence of percentiles to compute (0-100)

        Returns:
            Percentile value(s)

        Raises:
            TypeError: If input cannot be converted to numeric array
            ValueError: If percentile values are invalid or input is empty
        """
        array = self._validate_input(data)
        axis = self._get_axis_param()

        if axis is not None:
            axis = _validate_axis(axis, array.ndim)

        # Get percentile values from parameters or argument
        if "q" in self.parameters:
            q = self.parameters["q"]

        # Validate percentile values
        if isinstance(q, (int, float)):
            if not (0 <= q <= 100):
                raise ValueError(f"Percentile must be between 0 and 100, got {q}")
        elif isinstance(q, (list, tuple)):
            q = np.array(q)
            if not np.all((0 <= q) & (q <= 100)):
                raise ValueError("All percentile values must be between 0 and 100")
        else:
            try:
                q = float(q)
                if not (0 <= q <= 100):
                    raise ValueError(f"Percentile must be between 0 and 100, got {q}")
            except (ValueError, TypeError):
                raise ValueError(f"Invalid percentile value: {q}")

        try:
            if self.stat_config.nan_handling == "omit":
                result = np.nanpercentile(
                    array, q, axis=axis,
                    method=self.stat_config.interpolation,
                    keepdims=self.stat_config.keepdims
                )
            else:
                result = np.percentile(
                    array, q, axis=axis,
                    method=self.stat_config.interpolation,
                    keepdims=self.stat_config.keepdims
                )

            # Check for warnings
            if np.any(np.isnan(result)) and self.stat_config.nan_handling == "warn":
                warnings.warn("NaN values in percentile result", RuntimeWarning)

            return result

        except Exception as e:
            raise ValueError(f"Percentile calculation failed: {e}")


class StandardDeviationOperator(BaseStatisticalOperator):
    """Standard deviation operator (square root of variance)."""

    def evaluate(self, data: Any) -> Any:
        """
        Compute the standard deviation of the input data.

        Args:
            data: Input data array

        Returns:
            Standard deviation value or array

        Raises:
            TypeError: If input cannot be converted to numeric array
            ValueError: If input is empty or has invalid configuration
        """
        array = self._validate_input(data)
        axis = self._get_axis_param()

        if axis is not None:
            axis = _validate_axis(axis, array.ndim)

        try:
            if self.stat_config.nan_handling == "omit":
                result = np.nanstd(array, axis=axis, ddof=self.stat_config.ddof, keepdims=self.stat_config.keepdims)
            else:
                result = np.std(array, axis=axis, ddof=self.stat_config.ddof, keepdims=self.stat_config.keepdims)

            # Check for warnings
            if np.any(np.isnan(result)) and self.stat_config.nan_handling == "warn":
                warnings.warn("NaN values in standard deviation result", RuntimeWarning)

            return result

        except Exception as e:
            raise ValueError(f"Standard deviation calculation failed: {e}")


class MedianOperator(BaseStatisticalOperator):
    """Median operator (50th percentile)."""

    def evaluate(self, data: Any) -> Any:
        """
        Compute the median of the input data.

        Args:
            data: Input data array

        Returns:
            Median value or array

        Raises:
            TypeError: If input cannot be converted to numeric array
            ValueError: If input is empty
        """
        array = self._validate_input(data)
        axis = self._get_axis_param()

        if axis is not None:
            axis = _validate_axis(axis, array.ndim)

        try:
            if self.stat_config.nan_handling == "omit":
                result = np.nanmedian(array, axis=axis, keepdims=self.stat_config.keepdims)
            else:
                result = np.median(array, axis=axis, keepdims=self.stat_config.keepdims)

            # Check for warnings
            if np.any(np.isnan(result)) and self.stat_config.nan_handling == "warn":
                warnings.warn("NaN values in median result", RuntimeWarning)

            return result

        except Exception as e:
            raise ValueError(f"Median calculation failed: {e}")