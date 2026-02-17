"""
Mathematical operator implementations for ESM Format.

This module provides implementations for basic arithmetic operations
with proper type checking, broadcasting rules, and numerical precision handling.
"""

import warnings
import numpy as np
from typing import Any, Union, List, Dict, Optional
from dataclasses import dataclass

from .esm_types import Operator, OperatorType


def _ensure_numeric(value: Any) -> Union[int, float, np.ndarray]:
    """
    Ensure a value is numeric and handle type conversions.

    Args:
        value: Input value to convert

    Returns:
        Numeric value (int, float, or numpy array)

    Raises:
        TypeError: If value cannot be converted to a numeric type
        ValueError: If conversion results in invalid numeric value
    """
    if isinstance(value, (int, float)):
        return value
    elif isinstance(value, np.ndarray):
        if not np.issubdtype(value.dtype, np.number):
            raise TypeError(f"Array must contain numeric values, got dtype: {value.dtype}")
        return value
    elif isinstance(value, (list, tuple)):
        try:
            return np.array(value, dtype=float)
        except (ValueError, TypeError) as e:
            raise TypeError(f"Cannot convert sequence to numeric array: {e}")
    elif isinstance(value, str):
        try:
            # Try int first, then float
            if '.' in value or 'e' in value.lower():
                return float(value)
            else:
                return int(value)
        except ValueError:
            raise TypeError(f"Cannot convert string '{value}' to numeric value")
    else:
        try:
            # Try numpy conversion as last resort
            return np.asarray(value, dtype=float)
        except (ValueError, TypeError):
            raise TypeError(f"Cannot convert {type(value).__name__} to numeric value")


def _check_broadcasting_compatibility(a: Any, b: Any) -> bool:
    """
    Check if two values are compatible for numpy broadcasting.

    Args:
        a, b: Values to check for broadcasting compatibility

    Returns:
        True if broadcasting is possible, False otherwise
    """
    try:
        # Convert to arrays if needed
        arr_a = np.asarray(a) if not isinstance(a, np.ndarray) else a
        arr_b = np.asarray(b) if not isinstance(b, np.ndarray) else b

        # Check broadcasting
        np.broadcast_shapes(arr_a.shape, arr_b.shape)
        return True
    except ValueError:
        return False


def _handle_precision_warnings(result: Any, operation: str, operands: List[Any]) -> Any:
    """
    Handle precision warnings for mathematical operations.

    Args:
        result: Result of the operation
        operation: Name of the operation
        operands: Input operands

    Returns:
        Result with appropriate warnings if precision issues detected
    """
    if isinstance(result, np.ndarray):
        # Check for overflow
        if np.any(np.isinf(result)):
            warnings.warn(f"Overflow detected in {operation} operation", RuntimeWarning)

        # Check for underflow (very small numbers)
        if np.any((result != 0) & (np.abs(result) < np.finfo(result.dtype).tiny)):
            warnings.warn(f"Underflow detected in {operation} operation", RuntimeWarning)

        # Check for NaN
        if np.any(np.isnan(result)):
            warnings.warn(f"NaN values produced in {operation} operation", RuntimeWarning)

    return result


@dataclass
class ArithmeticOperatorConfig:
    """Configuration for arithmetic operators."""
    precision: str = "double"  # "single", "double", "extended"
    overflow_handling: str = "warn"  # "ignore", "warn", "raise"
    underflow_handling: str = "warn"  # "ignore", "warn", "raise"
    nan_handling: str = "warn"  # "ignore", "warn", "raise", "propagate"
    broadcasting: bool = True


class BaseArithmeticOperator:
    """
    Base class for arithmetic operators.

    Provides common functionality for type checking, broadcasting,
    and precision handling.
    """

    def __init__(self, config: Operator):
        """
        Initialize the arithmetic operator.

        Args:
            config: Operator configuration
        """
        self.config = config
        self.name = config.name
        self.parameters = config.parameters
        self.input_variables = config.input_variables
        self.output_variables = config.output_variables

        # Parse arithmetic-specific configuration
        self.arith_config = ArithmeticOperatorConfig()
        if "precision" in self.parameters:
            self.arith_config.precision = self.parameters["precision"]
        if "overflow_handling" in self.parameters:
            self.arith_config.overflow_handling = self.parameters["overflow_handling"]
        if "underflow_handling" in self.parameters:
            self.arith_config.underflow_handling = self.parameters["underflow_handling"]
        if "nan_handling" in self.parameters:
            self.arith_config.nan_handling = self.parameters["nan_handling"]
        if "broadcasting" in self.parameters:
            self.arith_config.broadcasting = self.parameters["broadcasting"]

    def _validate_inputs(self, *operands) -> List[Any]:
        """
        Validate and prepare input operands.

        Args:
            *operands: Input operands to validate

        Returns:
            List of validated numeric operands

        Raises:
            TypeError: If operands are not numeric or broadcasting is incompatible
            ValueError: If operands have invalid values
        """
        validated = []

        for operand in operands:
            try:
                numeric_operand = _ensure_numeric(operand)
                validated.append(numeric_operand)
            except TypeError as e:
                raise TypeError(f"Invalid operand in {self.name}: {e}")

        # Check broadcasting compatibility if enabled
        if self.arith_config.broadcasting and len(validated) > 1:
            for i in range(len(validated) - 1):
                if not _check_broadcasting_compatibility(validated[i], validated[i + 1]):
                    shapes = [np.asarray(v).shape for v in validated]
                    raise TypeError(
                        f"Broadcasting incompatible shapes in {self.name}: {shapes}"
                    )

        return validated

    def _apply_precision(self, result: Any) -> Any:
        """
        Apply precision settings to result.

        Args:
            result: Result to apply precision to

        Returns:
            Result with appropriate precision
        """
        if isinstance(result, np.ndarray):
            if self.arith_config.precision == "single":
                return result.astype(np.float32)
            elif self.arith_config.precision == "double":
                return result.astype(np.float64)
            elif self.arith_config.precision == "extended":
                return result.astype(np.longdouble)
        elif isinstance(result, (int, float)):
            # Convert scalar to array to apply precision, then back to scalar if needed
            arr = np.array(result)
            if self.arith_config.precision == "single":
                arr = arr.astype(np.float32)
            elif self.arith_config.precision == "double":
                arr = arr.astype(np.float64)
            elif self.arith_config.precision == "extended":
                arr = arr.astype(np.longdouble)
            return arr

        return result

    def evaluate(self, *operands) -> Any:
        """
        Evaluate the operator with given operands.

        This method should be implemented by subclasses.

        Args:
            *operands: Input operands

        Returns:
            Result of the operation
        """
        raise NotImplementedError("Subclasses must implement evaluate method")


class AddOperator(BaseArithmeticOperator):
    """Addition operator with broadcasting and precision handling."""

    def evaluate(self, *operands) -> Any:
        """
        Perform addition operation.

        Args:
            *operands: Numeric operands to add

        Returns:
            Sum of all operands
        """
        if len(operands) < 2:
            raise ValueError(f"Addition requires at least 2 operands, got {len(operands)}")

        validated = self._validate_inputs(*operands)

        try:
            # Perform addition
            result = validated[0]
            for operand in validated[1:]:
                result = np.add(result, operand)

            # Apply precision settings
            result = self._apply_precision(result)

            # Handle precision warnings
            result = _handle_precision_warnings(result, "addition", validated)

            return result

        except Exception as e:
            raise ValueError(f"Addition operation failed: {e}")

    def __str__(self):
        return f"Add(precision={self.arith_config.precision}, broadcasting={self.arith_config.broadcasting})"


class SubtractOperator(BaseArithmeticOperator):
    """Subtraction operator with broadcasting and precision handling."""

    def evaluate(self, *operands) -> Any:
        """
        Perform subtraction operation.

        Args:
            *operands: Numeric operands (first - second - third - ...)

        Returns:
            Result of subtraction
        """
        if len(operands) < 2:
            raise ValueError(f"Subtraction requires at least 2 operands, got {len(operands)}")

        validated = self._validate_inputs(*operands)

        try:
            # Perform subtraction
            result = validated[0]
            for operand in validated[1:]:
                result = np.subtract(result, operand)

            # Apply precision settings
            result = self._apply_precision(result)

            # Handle precision warnings
            result = _handle_precision_warnings(result, "subtraction", validated)

            return result

        except Exception as e:
            raise ValueError(f"Subtraction operation failed: {e}")

    def __str__(self):
        return f"Subtract(precision={self.arith_config.precision}, broadcasting={self.arith_config.broadcasting})"


class MultiplyOperator(BaseArithmeticOperator):
    """Multiplication operator with broadcasting and precision handling."""

    def evaluate(self, *operands) -> Any:
        """
        Perform multiplication operation.

        Args:
            *operands: Numeric operands to multiply

        Returns:
            Product of all operands
        """
        if len(operands) < 2:
            raise ValueError(f"Multiplication requires at least 2 operands, got {len(operands)}")

        validated = self._validate_inputs(*operands)

        try:
            # Perform multiplication
            result = validated[0]
            for operand in validated[1:]:
                result = np.multiply(result, operand)

            # Apply precision settings
            result = self._apply_precision(result)

            # Handle precision warnings
            result = _handle_precision_warnings(result, "multiplication", validated)

            return result

        except Exception as e:
            raise ValueError(f"Multiplication operation failed: {e}")

    def __str__(self):
        return f"Multiply(precision={self.arith_config.precision}, broadcasting={self.arith_config.broadcasting})"


class DivideOperator(BaseArithmeticOperator):
    """Division operator with broadcasting, precision, and divide-by-zero handling."""

    def evaluate(self, *operands) -> Any:
        """
        Perform division operation.

        Args:
            *operands: Numeric operands (first / second / third / ...)

        Returns:
            Result of division
        """
        if len(operands) < 2:
            raise ValueError(f"Division requires at least 2 operands, got {len(operands)}")

        validated = self._validate_inputs(*operands)

        try:
            # Check for division by zero
            for i, operand in enumerate(validated[1:], 1):
                operand_arr = np.asarray(operand)
                if np.any(operand_arr == 0):
                    if self.arith_config.nan_handling == "raise":
                        raise ValueError(f"Division by zero in operand {i}")
                    elif self.arith_config.nan_handling == "warn":
                        warnings.warn(f"Division by zero detected in operand {i}", RuntimeWarning)

            # Perform division with warning suppression to avoid duplicate numpy warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                result = validated[0]
                for operand in validated[1:]:
                    result = np.divide(result, operand)

            # Apply precision settings
            result = self._apply_precision(result)

            # Handle precision warnings (but skip overflow warnings for division by zero cases)
            if not np.any(np.isinf(result)):
                result = _handle_precision_warnings(result, "division", validated)

            return result

        except Exception as e:
            raise ValueError(f"Division operation failed: {e}")

    def __str__(self):
        return f"Divide(precision={self.arith_config.precision}, broadcasting={self.arith_config.broadcasting})"