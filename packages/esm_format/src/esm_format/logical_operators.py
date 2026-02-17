"""
Logical operator implementations for ESM Format.

This module provides implementations for logical operations (and, or, not)
and comparison operations (eq, ne, lt, le, gt, ge) with proper boolean logic,
short-circuiting, and type coercion rules.
"""

import warnings
import numpy as np
from typing import Any, Union, List, Dict, Optional, Tuple
from dataclasses import dataclass

from .esm_types import Operator, OperatorType


def _coerce_to_boolean(value: Any) -> Union[bool, np.ndarray]:
    """
    Coerce a value to boolean following Python's truthiness rules.

    Args:
        value: Input value to convert to boolean

    Returns:
        Boolean value or numpy boolean array

    Raises:
        TypeError: If value cannot be converted to boolean
    """
    if isinstance(value, (bool, np.bool_)):
        return value
    elif isinstance(value, (int, float)):
        return bool(value)
    elif isinstance(value, np.ndarray):
        # Convert to boolean array
        if np.issubdtype(value.dtype, np.number):
            return value != 0
        elif np.issubdtype(value.dtype, np.bool_):
            return value
        else:
            # Try to convert to numeric first, then boolean
            try:
                numeric_array = value.astype(float)
                return numeric_array != 0
            except (ValueError, TypeError):
                raise TypeError(f"Cannot convert array with dtype {value.dtype} to boolean")
    elif isinstance(value, (list, tuple)):
        # Convert to array first, then to boolean
        try:
            arr = np.array(value)
            return _coerce_to_boolean(arr)
        except (ValueError, TypeError):
            raise TypeError(f"Cannot convert sequence to boolean array")
    elif isinstance(value, str):
        # Strings: empty string is False, non-empty is True
        return bool(value)
    elif value is None:
        return False
    else:
        # Use Python's built-in bool() function for other types
        try:
            return bool(value)
        except Exception:
            raise TypeError(f"Cannot convert {type(value).__name__} to boolean")


def _ensure_comparable(a: Any, b: Any) -> Tuple[Any, Any]:
    """
    Ensure two values are comparable by performing type coercion.

    Args:
        a, b: Values to make comparable

    Returns:
        Tuple of (coerced_a, coerced_b)

    Raises:
        TypeError: If values cannot be made comparable
    """
    # Handle None values
    if a is None and b is None:
        return None, None
    elif a is None or b is None:
        # None is only equal to None, less than everything else
        return a, b

    # If both are the same type, they're usually comparable
    # But for arrays/lists, we still need to check broadcasting compatibility
    if type(a) == type(b):
        if not isinstance(a, (np.ndarray, list, tuple)):
            return a, b
        # For arrays/lists of same type, still check broadcasting
        # Fall through to array handling

    # Handle numeric comparisons first - if either operand is numeric, try to convert both
    numeric_a = isinstance(a, (int, float, np.number, np.ndarray))
    numeric_b = isinstance(b, (int, float, np.number, np.ndarray))

    # If at least one is numeric, try to make both numeric
    if numeric_a or numeric_b:
        try:
            # Try to convert string operands to numeric
            if isinstance(a, str):
                try:
                    a = float(a) if '.' in a or 'e' in a.lower() else int(a)
                    numeric_a = True
                except ValueError:
                    # String can't be converted to number, fall through to string comparison
                    numeric_a = False

            if isinstance(b, str):
                try:
                    b = float(b) if '.' in b or 'e' in b.lower() else int(b)
                    numeric_b = True
                except ValueError:
                    # String can't be converted to number, fall through to string comparison
                    numeric_b = False

            # If both are now numeric, convert to numpy arrays
            if numeric_a and numeric_b:
                a_arr = np.asarray(a)
                b_arr = np.asarray(b)
                return a_arr, b_arr

        except (ValueError, TypeError):
            pass  # Fall through to other comparisons

    # Handle string comparisons if numeric conversion didn't work
    if isinstance(a, str) or isinstance(b, str):
        # Convert both to strings for string comparison
        return str(a), str(b)

    # Handle arrays - only real array-like objects, not arbitrary objects that numpy can wrap
    if isinstance(a, (np.ndarray, list, tuple)) or isinstance(b, (np.ndarray, list, tuple)):
        # But skip if one operand is a complex object that would create an object array
        if (not isinstance(a, (np.ndarray, list, tuple, int, float, str, type(None))) or
            not isinstance(b, (np.ndarray, list, tuple, int, float, str, type(None)))):
            # Fall back to string comparison for complex objects
            return str(a), str(b)

        try:
            a_arr = np.asarray(a)
            b_arr = np.asarray(b)

            # Check if arrays have compatible shapes for broadcasting
            try:
                np.broadcast_shapes(a_arr.shape, b_arr.shape)
                return a_arr, b_arr
            except ValueError:
                raise TypeError(f"Arrays with shapes {a_arr.shape} and {b_arr.shape} are not broadcastable")
        except TypeError:
            # Re-raise TypeError (broadcasting incompatibility)
            raise
        except Exception:
            # Fall back to string comparison for other errors
            return str(a), str(b)

    # For other types, use string representation
    return str(a), str(b)


@dataclass
class LogicalOperatorConfig:
    """Configuration for logical operators."""
    short_circuit: bool = True  # Enable short-circuit evaluation
    strict_types: bool = False  # Require strict boolean types (no coercion)
    nan_handling: str = "propagate"  # "ignore", "warn", "raise", "propagate"


class BaseLogicalOperator:
    """
    Base class for logical operators.

    Provides common functionality for type coercion, boolean conversion,
    and configuration management.
    """

    def __init__(self, config: Operator):
        """
        Initialize the logical operator.

        Args:
            config: Operator configuration
        """
        self.config = config
        self.name = config.name
        self.parameters = config.parameters
        self.input_variables = config.input_variables
        self.output_variables = config.output_variables

        # Parse logical-specific configuration
        self.logical_config = LogicalOperatorConfig()
        if "short_circuit" in self.parameters:
            self.logical_config.short_circuit = self.parameters["short_circuit"]
        if "strict_types" in self.parameters:
            self.logical_config.strict_types = self.parameters["strict_types"]
        if "nan_handling" in self.parameters:
            self.logical_config.nan_handling = self.parameters["nan_handling"]

    def _validate_and_coerce(self, *operands) -> List[Any]:
        """
        Validate and coerce operands to appropriate types.

        Args:
            *operands: Input operands to validate and coerce

        Returns:
            List of validated/coerced operands

        Raises:
            TypeError: If operands cannot be coerced appropriately
            ValueError: If operands have invalid values
        """
        if self.logical_config.strict_types:
            # Strict mode: only accept boolean types
            validated = []
            for operand in operands:
                if not isinstance(operand, (bool, np.bool_, np.ndarray)):
                    raise TypeError(f"Strict mode: expected boolean type, got {type(operand).__name__}")
                if isinstance(operand, np.ndarray) and not np.issubdtype(operand.dtype, np.bool_):
                    raise TypeError(f"Strict mode: expected boolean array, got array with dtype {operand.dtype}")
                validated.append(operand)
        else:
            # Coercion mode: convert to boolean
            validated = []
            for operand in operands:
                try:
                    boolean_operand = _coerce_to_boolean(operand)
                    validated.append(boolean_operand)
                except TypeError as e:
                    raise TypeError(f"Cannot coerce operand in {self.name}: {e}")

        return validated

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


class AndOperator(BaseLogicalOperator):
    """Logical AND operator with short-circuit evaluation."""

    def evaluate(self, *operands) -> Any:
        """
        Perform logical AND operation.

        Args:
            *operands: Boolean operands to AND together

        Returns:
            Result of AND operation (boolean or boolean array)
        """
        if len(operands) < 2:
            raise ValueError(f"AND requires at least 2 operands, got {len(operands)}")

        validated = self._validate_and_coerce(*operands)

        try:
            if self.logical_config.short_circuit:
                # Short-circuit evaluation: stop at first False
                result = validated[0]
                for operand in validated[1:]:
                    if isinstance(result, np.ndarray) or isinstance(operand, np.ndarray):
                        # Array operations don't support short-circuiting
                        result = np.logical_and(result, operand)
                    else:
                        # Scalar short-circuiting
                        if not result:
                            return result
                        result = result and operand
            else:
                # Evaluate all operands
                result = validated[0]
                for operand in validated[1:]:
                    if isinstance(result, np.ndarray) or isinstance(operand, np.ndarray):
                        result = np.logical_and(result, operand)
                    else:
                        result = result and operand

            return result

        except Exception as e:
            raise ValueError(f"AND operation failed: {e}")

    def __str__(self):
        return f"And(short_circuit={self.logical_config.short_circuit}, strict={self.logical_config.strict_types})"


class OrOperator(BaseLogicalOperator):
    """Logical OR operator with short-circuit evaluation."""

    def evaluate(self, *operands) -> Any:
        """
        Perform logical OR operation.

        Args:
            *operands: Boolean operands to OR together

        Returns:
            Result of OR operation (boolean or boolean array)
        """
        if len(operands) < 2:
            raise ValueError(f"OR requires at least 2 operands, got {len(operands)}")

        validated = self._validate_and_coerce(*operands)

        try:
            if self.logical_config.short_circuit:
                # Short-circuit evaluation: stop at first True
                result = validated[0]
                for operand in validated[1:]:
                    if isinstance(result, np.ndarray) or isinstance(operand, np.ndarray):
                        # Array operations don't support short-circuiting
                        result = np.logical_or(result, operand)
                    else:
                        # Scalar short-circuiting
                        if result:
                            return result
                        result = result or operand
            else:
                # Evaluate all operands
                result = validated[0]
                for operand in validated[1:]:
                    if isinstance(result, np.ndarray) or isinstance(operand, np.ndarray):
                        result = np.logical_or(result, operand)
                    else:
                        result = result or operand

            return result

        except Exception as e:
            raise ValueError(f"OR operation failed: {e}")

    def __str__(self):
        return f"Or(short_circuit={self.logical_config.short_circuit}, strict={self.logical_config.strict_types})"


class NotOperator(BaseLogicalOperator):
    """Logical NOT operator."""

    def evaluate(self, *operands) -> Any:
        """
        Perform logical NOT operation.

        Args:
            *operands: Single boolean operand to negate

        Returns:
            Negated boolean value or boolean array
        """
        if len(operands) != 1:
            raise ValueError(f"NOT requires exactly 1 operand, got {len(operands)}")

        validated = self._validate_and_coerce(*operands)
        operand = validated[0]

        try:
            if isinstance(operand, np.ndarray):
                return np.logical_not(operand)
            else:
                return not operand

        except Exception as e:
            raise ValueError(f"NOT operation failed: {e}")

    def __str__(self):
        return f"Not(strict={self.logical_config.strict_types})"


class BaseComparisonOperator(BaseLogicalOperator):
    """
    Base class for comparison operators.

    Provides common functionality for type coercion and comparison handling.
    """

    def _validate_and_prepare_comparison(self, *operands) -> List[Any]:
        """
        Validate and prepare operands for comparison.

        Args:
            *operands: Input operands to prepare

        Returns:
            List of prepared operands

        Raises:
            TypeError: If operands cannot be made comparable
            ValueError: If operands have invalid values
        """
        if len(operands) != 2:
            raise ValueError(f"{self.name} requires exactly 2 operands, got {len(operands)}")

        a, b = operands
        try:
            return list(_ensure_comparable(a, b))
        except TypeError as e:
            raise TypeError(f"Cannot compare operands in {self.name}: {e}")


class EqualOperator(BaseComparisonOperator):
    """Equality comparison operator."""

    def evaluate(self, *operands) -> Any:
        """
        Perform equality comparison.

        Args:
            *operands: Two operands to compare for equality

        Returns:
            Boolean result of equality comparison
        """
        a, b = self._validate_and_prepare_comparison(*operands)

        try:
            # Handle None comparisons
            if a is None or b is None:
                return a is b

            # Use numpy for array comparisons
            if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
                return np.equal(a, b)
            else:
                return a == b

        except Exception as e:
            raise ValueError(f"Equality comparison failed: {e}")

    def __str__(self):
        return "Equal()"


class NotEqualOperator(BaseComparisonOperator):
    """Not-equal comparison operator."""

    def evaluate(self, *operands) -> Any:
        """
        Perform not-equal comparison.

        Args:
            *operands: Two operands to compare for inequality

        Returns:
            Boolean result of inequality comparison
        """
        a, b = self._validate_and_prepare_comparison(*operands)

        try:
            # Handle None comparisons
            if a is None or b is None:
                return a is not b

            # Use numpy for array comparisons
            if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
                return np.not_equal(a, b)
            else:
                return a != b

        except Exception as e:
            raise ValueError(f"Not-equal comparison failed: {e}")

    def __str__(self):
        return "NotEqual()"


class LessThanOperator(BaseComparisonOperator):
    """Less-than comparison operator."""

    def evaluate(self, *operands) -> Any:
        """
        Perform less-than comparison.

        Args:
            *operands: Two operands to compare (first < second)

        Returns:
            Boolean result of less-than comparison
        """
        a, b = self._validate_and_prepare_comparison(*operands)

        try:
            # Handle None comparisons (None is less than everything except None)
            if a is None and b is None:
                return False
            elif a is None:
                return True
            elif b is None:
                return False

            # Use numpy for array comparisons
            if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
                return np.less(a, b)
            else:
                return a < b

        except Exception as e:
            raise ValueError(f"Less-than comparison failed: {e}")

    def __str__(self):
        return "LessThan()"


class LessThanOrEqualOperator(BaseComparisonOperator):
    """Less-than-or-equal comparison operator."""

    def evaluate(self, *operands) -> Any:
        """
        Perform less-than-or-equal comparison.

        Args:
            *operands: Two operands to compare (first <= second)

        Returns:
            Boolean result of less-than-or-equal comparison
        """
        a, b = self._validate_and_prepare_comparison(*operands)

        try:
            # Handle None comparisons
            if a is None and b is None:
                return True
            elif a is None:
                return True
            elif b is None:
                return False

            # Use numpy for array comparisons
            if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
                return np.less_equal(a, b)
            else:
                return a <= b

        except Exception as e:
            raise ValueError(f"Less-than-or-equal comparison failed: {e}")

    def __str__(self):
        return "LessThanOrEqual()"


class GreaterThanOperator(BaseComparisonOperator):
    """Greater-than comparison operator."""

    def evaluate(self, *operands) -> Any:
        """
        Perform greater-than comparison.

        Args:
            *operands: Two operands to compare (first > second)

        Returns:
            Boolean result of greater-than comparison
        """
        a, b = self._validate_and_prepare_comparison(*operands)

        try:
            # Handle None comparisons
            if a is None and b is None:
                return False
            elif a is None:
                return False
            elif b is None:
                return True

            # Use numpy for array comparisons
            if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
                return np.greater(a, b)
            else:
                return a > b

        except Exception as e:
            raise ValueError(f"Greater-than comparison failed: {e}")

    def __str__(self):
        return "GreaterThan()"


class GreaterThanOrEqualOperator(BaseComparisonOperator):
    """Greater-than-or-equal comparison operator."""

    def evaluate(self, *operands) -> Any:
        """
        Perform greater-than-or-equal comparison.

        Args:
            *operands: Two operands to compare (first >= second)

        Returns:
            Boolean result of greater-than-or-equal comparison
        """
        a, b = self._validate_and_prepare_comparison(*operands)

        try:
            # Handle None comparisons
            if a is None and b is None:
                return True
            elif a is None:
                return False
            elif b is None:
                return True

            # Use numpy for array comparisons
            if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
                return np.greater_equal(a, b)
            else:
                return a >= b

        except Exception as e:
            raise ValueError(f"Greater-than-or-equal comparison failed: {e}")

    def __str__(self):
        return "GreaterThanOrEqual()"