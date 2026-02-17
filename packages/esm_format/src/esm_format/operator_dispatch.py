"""
Operator dispatch system for ESM Format.

This module implements operator overloading and polymorphism through type-based
dispatch, allowing automatic selection of appropriate operator implementations
based on input types with fallback mechanisms.
"""

import inspect
import warnings
from typing import Any, Dict, List, Type, Union, Tuple, Optional, Callable, Set
from collections import defaultdict
from dataclasses import dataclass
import numpy as np

from .esm_types import Operator, OperatorType
from .operator_registry import get_registry


@dataclass
class TypeSignature:
    """Type signature for operator dispatch."""
    input_types: Tuple[Type, ...]
    output_type: Optional[Type] = None
    specificity: int = 0  # Higher means more specific match

    def __post_init__(self):
        """Calculate specificity score for this signature."""
        self.specificity = self._calculate_specificity()

    def _calculate_specificity(self) -> int:
        """
        Calculate specificity score based on type hierarchy.
        More specific types get higher scores.
        """
        score = 0
        for typ in self.input_types:
            # Basic scoring system - more specific types get higher scores
            if typ == Any:
                score += 0
            elif typ in (int, float, complex, str):
                score += 10
            elif typ == np.ndarray:
                score += 8
            elif hasattr(typ, '__mro__'):
                # Count inheritance depth (deeper = more specific)
                score += len(typ.__mro__)
            else:
                score += 5
        return score

    def matches(self, input_types: Tuple[Type, ...]) -> bool:
        """Check if this signature matches the given input types."""
        if len(input_types) != len(self.input_types):
            return False

        for provided, expected in zip(input_types, self.input_types):
            if not self._type_compatible(provided, expected):
                return False
        return True

    def _type_compatible(self, provided: Type, expected: Type) -> bool:
        """Check if provided type is compatible with expected type."""
        if expected == Any:
            return True
        if provided == expected:
            return True

        # Handle tuple of types (union-like behavior)
        if isinstance(expected, tuple):
            return any(self._type_compatible(provided, exp_type) for exp_type in expected)

        if isinstance(provided, type) and isinstance(expected, type):
            return issubclass(provided, expected)
        return False


@dataclass
class OperatorOverload:
    """Represents a specific operator implementation for given types."""
    signature: TypeSignature
    implementation: Callable
    operator_class: Type
    priority: int = 0  # Higher priority implementations are preferred
    description: Optional[str] = None


class OperatorDispatcher:
    """
    Central dispatcher for operator overloading and polymorphism.

    Manages multiple implementations of operators based on input types,
    provides automatic dispatch, and handles fallback mechanisms.
    """

    def __init__(self):
        """Initialize the operator dispatcher."""
        self._overloads: Dict[str, List[OperatorOverload]] = defaultdict(list)
        self._fallback_chains: Dict[str, List[str]] = defaultdict(list)
        self._registry = get_registry()

        # Cache for dispatch decisions to improve performance
        self._dispatch_cache: Dict[Tuple[str, Tuple[Type, ...]], OperatorOverload] = {}

        # Register built-in operator overloads
        self._register_builtin_overloads()

    def _register_builtin_overloads(self):
        """Register built-in operator overloads for common type combinations."""
        # This will be populated with common overloads
        # For now, we'll register basic arithmetic overloads

        # Scalar arithmetic (int, float)
        self.register_overload(
            "add",
            TypeSignature((int, int)),
            self._scalar_add,
            priority=10,
            description="Integer addition"
        )

        self.register_overload(
            "add",
            TypeSignature((float, float)),
            self._scalar_add,
            priority=10,
            description="Float addition"
        )

        self.register_overload(
            "add",
            TypeSignature((int, float)),
            self._scalar_add,
            priority=8,
            description="Mixed int-float addition"
        )

        self.register_overload(
            "add",
            TypeSignature((float, int)),
            self._scalar_add,
            priority=8,
            description="Mixed float-int addition"
        )

        # Array arithmetic (numpy arrays)
        self.register_overload(
            "add",
            TypeSignature((np.ndarray, np.ndarray)),
            self._array_add,
            priority=10,
            description="NumPy array addition"
        )

        self.register_overload(
            "add",
            TypeSignature((np.ndarray, (int, float))),
            self._array_scalar_add,
            priority=9,
            description="Array-scalar addition"
        )

        # Similar patterns for other arithmetic operators
        for op_name in ["subtract", "multiply", "divide"]:
            method = getattr(self, f"_scalar_{op_name}", self._scalar_generic)
            array_method = getattr(self, f"_array_{op_name}", self._array_generic)

            # Register scalar overloads
            self.register_overload(op_name, TypeSignature((int, int)), method, priority=10)
            self.register_overload(op_name, TypeSignature((float, float)), method, priority=10)
            self.register_overload(op_name, TypeSignature((int, float)), method, priority=8)
            self.register_overload(op_name, TypeSignature((float, int)), method, priority=8)

            # Register array overloads
            self.register_overload(op_name, TypeSignature((np.ndarray, np.ndarray)), array_method, priority=10)
            self.register_overload(op_name, TypeSignature((np.ndarray, (int, float))), array_method, priority=9)

    def register_overload(
        self,
        operator_name: str,
        signature: TypeSignature,
        implementation: Callable,
        operator_class: Optional[Type] = None,
        priority: int = 0,
        description: Optional[str] = None
    ):
        """
        Register an operator overload for specific types.

        Args:
            operator_name: Name of the operator
            signature: Type signature for this overload
            implementation: Function implementing the operation
            operator_class: Optional operator class (for compatibility)
            priority: Priority of this implementation (higher = preferred)
            description: Optional description
        """
        overload = OperatorOverload(
            signature=signature,
            implementation=implementation,
            operator_class=operator_class,
            priority=priority,
            description=description
        )

        self._overloads[operator_name].append(overload)

        # Sort overloads by priority and specificity (descending)
        self._overloads[operator_name].sort(
            key=lambda x: (x.priority, x.signature.specificity),
            reverse=True
        )

        # Clear cache as new overload might change dispatch decisions
        self._dispatch_cache.clear()

    def register_fallback_chain(self, operator_name: str, fallback_operators: List[str]):
        """
        Register a fallback chain for an operator.

        Args:
            operator_name: Primary operator name
            fallback_operators: List of fallback operators to try in order
        """
        self._fallback_chains[operator_name] = fallback_operators

    def dispatch(self, operator_name: str, *args, **kwargs) -> Any:
        """
        Dispatch operator call to appropriate implementation.

        Args:
            operator_name: Name of the operator to call
            *args: Arguments to the operator
            **kwargs: Keyword arguments to the operator

        Returns:
            Result of the operator call

        Raises:
            ValueError: If no suitable implementation found
            TypeError: If argument types are incompatible
        """
        return self._dispatch_with_recursion_check(operator_name, set(), *args, **kwargs)

    def _dispatch_with_recursion_check(self, operator_name: str, visited_ops: set, *args, **kwargs) -> Any:
        """
        Internal dispatch method with recursion protection.

        Args:
            operator_name: Name of the operator to call
            visited_ops: Set of operators already visited (for recursion detection)
            *args: Arguments to the operator
            **kwargs: Keyword arguments to the operator

        Returns:
            Result of the operator call

        Raises:
            ValueError: If no suitable implementation found or circular dependency detected
            TypeError: If argument types are incompatible
        """
        if not args:
            raise ValueError(f"No arguments provided for operator '{operator_name}'")

        # Check for circular fallback dependency
        if operator_name in visited_ops:
            raise ValueError(f"Circular fallback dependency detected involving: {visited_ops}")

        # Get input types
        input_types = tuple(type(arg) for arg in args)
        cache_key = (operator_name, input_types)

        # Check cache first
        if cache_key in self._dispatch_cache:
            overload = self._dispatch_cache[cache_key]
            return self._call_implementation(overload, args, kwargs)

        # Find best matching overload
        overload = self._find_best_overload(operator_name, input_types)

        if overload:
            # Cache the decision
            self._dispatch_cache[cache_key] = overload
            return self._call_implementation(overload, args, kwargs)

        # Try fallback operators with recursion protection
        visited_ops_copy = visited_ops.copy()
        visited_ops_copy.add(operator_name)

        for fallback_op in self._fallback_chains.get(operator_name, []):
            try:
                return self._dispatch_with_recursion_check(fallback_op, visited_ops_copy, *args, **kwargs)
            except (ValueError, TypeError):
                continue

        # If no overload found, try to use registry operators as fallback
        if self._registry.has_operator(operator_name):
            try:
                operator_instance = self._registry.create_operator_by_name(
                    operator_name,
                    OperatorType.ARITHMETIC,  # Default type - should be improved
                    parameters={},
                    input_variables=[f"arg_{i}" for i in range(len(args))],
                    output_variables=["result"]
                )
                return operator_instance.evaluate(*args, **kwargs)
            except Exception as e:
                warnings.warn(f"Registry fallback failed for {operator_name}: {e}")

        # If all else fails, raise error
        available_sigs = [overload.signature.input_types for overload in self._overloads[operator_name]]
        raise TypeError(
            f"No implementation of '{operator_name}' found for types {input_types}. "
            f"Available signatures: {available_sigs}"
        )

    def _find_best_overload(self, operator_name: str, input_types: Tuple[Type, ...]) -> Optional[OperatorOverload]:
        """Find the best matching overload for given types."""
        if operator_name not in self._overloads:
            return None

        candidates = []
        for overload in self._overloads[operator_name]:
            if overload.signature.matches(input_types):
                candidates.append(overload)

        if not candidates:
            return None

        # Return the best candidate (already sorted by priority and specificity)
        return candidates[0]

    def _call_implementation(self, overload: OperatorOverload, args: tuple, kwargs: dict) -> Any:
        """Call the implementation with proper error handling."""
        try:
            return overload.implementation(*args, **kwargs)
        except Exception as e:
            # Add context to the error
            raise type(e)(
                f"Error in {overload.description or 'operator'} "
                f"with signature {overload.signature.input_types}: {e}"
            ) from e

    def get_available_overloads(self, operator_name: str) -> List[OperatorOverload]:
        """Get all available overloads for an operator."""
        return self._overloads.get(operator_name, []).copy()

    def clear_cache(self):
        """Clear the dispatch cache."""
        self._dispatch_cache.clear()

    def get_dispatch_info(self, operator_name: str, *args) -> Dict[str, Any]:
        """
        Get information about how an operator call would be dispatched.

        Args:
            operator_name: Name of the operator
            *args: Arguments that would be passed

        Returns:
            Dictionary with dispatch information
        """
        input_types = tuple(type(arg) for arg in args)
        overload = self._find_best_overload(operator_name, input_types)

        info = {
            "operator_name": operator_name,
            "input_types": input_types,
            "selected_overload": None,
            "available_overloads": len(self._overloads.get(operator_name, [])),
            "fallback_chain": self._fallback_chains.get(operator_name, []),
            "cache_hit": (operator_name, input_types) in self._dispatch_cache
        }

        if overload:
            info["selected_overload"] = {
                "signature": overload.signature.input_types,
                "priority": overload.priority,
                "specificity": overload.signature.specificity,
                "description": overload.description
            }

        return info

    # Built-in implementation methods
    def _scalar_add(self, a, b):
        """Basic scalar addition."""
        return a + b

    def _scalar_subtract(self, a, b):
        """Basic scalar subtraction."""
        return a - b

    def _scalar_multiply(self, a, b):
        """Basic scalar multiplication."""
        return a * b

    def _scalar_divide(self, a, b):
        """Basic scalar division with zero check."""
        if b == 0:
            raise ZeroDivisionError("Division by zero")
        return a / b

    def _scalar_generic(self, a, b, operation="unknown"):
        """Generic scalar operation fallback."""
        # This is a placeholder - specific operations should have their own methods
        raise NotImplementedError(f"Generic scalar operation '{operation}' not implemented")

    def _array_add(self, a, b):
        """NumPy array addition."""
        return np.add(a, b)

    def _array_subtract(self, a, b):
        """NumPy array subtraction."""
        return np.subtract(a, b)

    def _array_multiply(self, a, b):
        """NumPy array multiplication."""
        return np.multiply(a, b)

    def _array_divide(self, a, b):
        """NumPy array division."""
        with np.errstate(divide='raise', invalid='raise'):
            try:
                return np.divide(a, b)
            except FloatingPointError as e:
                raise ZeroDivisionError(f"Division error in array operation: {e}")

    def _array_scalar_add(self, a, b):
        """Array-scalar addition."""
        if isinstance(a, np.ndarray):
            return a + b
        else:
            return b + a

    def _array_generic(self, a, b, operation="unknown"):
        """Generic array operation fallback."""
        raise NotImplementedError(f"Generic array operation '{operation}' not implemented")


# Global dispatcher instance
_global_dispatcher = OperatorDispatcher()


def get_dispatcher() -> OperatorDispatcher:
    """Get the global operator dispatcher instance."""
    return _global_dispatcher


def dispatch_operator(operator_name: str, *args, **kwargs) -> Any:
    """
    Dispatch an operator call using the global dispatcher.

    Args:
        operator_name: Name of the operator to call
        *args: Arguments to the operator
        **kwargs: Keyword arguments to the operator

    Returns:
        Result of the operator call
    """
    return _global_dispatcher.dispatch(operator_name, *args, **kwargs)


def register_operator_overload(
    operator_name: str,
    input_types: Tuple[Type, ...],
    implementation: Callable,
    output_type: Optional[Type] = None,
    priority: int = 0,
    description: Optional[str] = None
):
    """
    Register an operator overload using the global dispatcher.

    Args:
        operator_name: Name of the operator
        input_types: Tuple of input types for this overload
        implementation: Function implementing the operation
        output_type: Optional output type
        priority: Priority of this implementation
        description: Optional description
    """
    signature = TypeSignature(input_types, output_type)
    _global_dispatcher.register_overload(
        operator_name, signature, implementation, None, priority, description
    )


def get_operator_overloads(operator_name: str) -> List[OperatorOverload]:
    """Get all available overloads for an operator."""
    return _global_dispatcher.get_available_overloads(operator_name)


def get_dispatch_info(operator_name: str, *args) -> Dict[str, Any]:
    """Get information about how an operator call would be dispatched."""
    return _global_dispatcher.get_dispatch_info(operator_name, *args)