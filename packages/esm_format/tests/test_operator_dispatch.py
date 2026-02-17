"""
Test cases for the operator dispatch system.

Tests operator overloading, polymorphism, type-based dispatch,
and fallback mechanisms.
"""

import pytest
import numpy as np
from typing import Any
from unittest.mock import Mock, patch

from esm_format.operator_dispatch import (
    OperatorDispatcher,
    TypeSignature,
    OperatorOverload,
    get_dispatcher,
    dispatch_operator,
    register_operator_overload,
    get_operator_overloads,
    get_dispatch_info,
)


class TestTypeSignature:
    """Test cases for TypeSignature class."""

    def test_signature_creation(self):
        """Test creating type signatures."""
        sig = TypeSignature((int, float))
        assert sig.input_types == (int, float)
        assert sig.output_type is None
        assert sig.specificity > 0

    def test_signature_with_output_type(self):
        """Test creating signatures with output types."""
        sig = TypeSignature((int, int), float)
        assert sig.input_types == (int, int)
        assert sig.output_type == float

    def test_signature_matching(self):
        """Test type signature matching."""
        sig = TypeSignature((int, float))

        assert sig.matches((int, float))
        assert not sig.matches((int, int))
        assert not sig.matches((int,))  # Wrong number of args
        assert not sig.matches((int, float, str))  # Too many args

    def test_signature_matching_with_any(self):
        """Test signature matching with Any type."""
        sig = TypeSignature((Any, int))

        assert sig.matches((str, int))
        assert sig.matches((float, int))
        assert sig.matches((list, int))
        assert not sig.matches((int, str))

    def test_signature_matching_inheritance(self):
        """Test signature matching with inheritance."""
        class Parent:
            pass

        class Child(Parent):
            pass

        sig = TypeSignature((Parent,))

        assert sig.matches((Parent,))
        assert sig.matches((Child,))  # Child should match Parent

    def test_specificity_calculation(self):
        """Test specificity scoring."""
        sig_any = TypeSignature((Any,))
        sig_int = TypeSignature((int,))
        sig_specific = TypeSignature((int, float))

        assert sig_int.specificity > sig_any.specificity
        assert sig_specific.specificity > sig_int.specificity


class TestOperatorDispatcher:
    """Test cases for OperatorDispatcher class."""

    def test_dispatcher_initialization(self):
        """Test dispatcher initializes with built-in overloads."""
        dispatcher = OperatorDispatcher()

        # Check that built-in overloads are registered
        add_overloads = dispatcher.get_available_overloads("add")
        assert len(add_overloads) > 0

        # Check that different type combinations are available
        signatures = [overload.signature.input_types for overload in add_overloads]
        assert (int, int) in signatures
        assert (float, float) in signatures

    def test_register_overload(self):
        """Test registering new operator overloads."""
        dispatcher = OperatorDispatcher()

        def string_concat(a: str, b: str) -> str:
            return a + b

        signature = TypeSignature((str, str), str)
        dispatcher.register_overload(
            "add",
            signature,
            string_concat,
            priority=5,
            description="String concatenation"
        )

        overloads = dispatcher.get_available_overloads("add")
        string_overloads = [o for o in overloads if o.signature.input_types == (str, str)]
        assert len(string_overloads) == 1
        assert string_overloads[0].description == "String concatenation"

    def test_dispatch_scalar_arithmetic(self):
        """Test dispatching scalar arithmetic operations."""
        dispatcher = OperatorDispatcher()

        # Test integer addition
        result = dispatcher.dispatch("add", 3, 5)
        assert result == 8

        # Test float addition
        result = dispatcher.dispatch("add", 3.5, 2.5)
        assert result == 6.0

        # Test mixed types
        result = dispatcher.dispatch("add", 3, 2.5)
        assert result == 5.5

    def test_dispatch_array_arithmetic(self):
        """Test dispatching array arithmetic operations."""
        dispatcher = OperatorDispatcher()

        # Test array addition
        a = np.array([1, 2, 3])
        b = np.array([4, 5, 6])
        result = dispatcher.dispatch("add", a, b)
        np.testing.assert_array_equal(result, [5, 7, 9])

        # Test array-scalar addition
        result = dispatcher.dispatch("add", a, 10)
        np.testing.assert_array_equal(result, [11, 12, 13])

    def test_dispatch_priority_ordering(self):
        """Test that higher priority overloads are selected."""
        dispatcher = OperatorDispatcher()

        def high_priority_add(a, b):
            return "high_priority"

        def low_priority_add(a, b):
            return "low_priority"

        signature = TypeSignature((int, int))

        dispatcher.register_overload("test_op", signature, low_priority_add, priority=1)
        dispatcher.register_overload("test_op", signature, high_priority_add, priority=10)

        result = dispatcher.dispatch("test_op", 1, 2)
        assert result == "high_priority"

    def test_dispatch_type_specificity(self):
        """Test that more specific types are preferred."""
        dispatcher = OperatorDispatcher()

        def generic_handler(a, b):
            return "generic"

        def specific_handler(a, b):
            return "specific"

        # Register generic handler with Any type
        dispatcher.register_overload("test_op", TypeSignature((Any, Any)), generic_handler)
        # Register specific handler with int types
        dispatcher.register_overload("test_op", TypeSignature((int, int)), specific_handler)

        result = dispatcher.dispatch("test_op", 1, 2)
        assert result == "specific"

    def test_dispatch_fallback_chain(self):
        """Test fallback chain functionality."""
        dispatcher = OperatorDispatcher()

        def fallback_op(a, b):
            return "fallback_result"

        # Register fallback operator
        dispatcher.register_overload("fallback_op", TypeSignature((int, int)), fallback_op)

        # Register fallback chain
        dispatcher.register_fallback_chain("unknown_op", ["fallback_op"])

        result = dispatcher.dispatch("unknown_op", 1, 2)
        assert result == "fallback_result"

    def test_dispatch_error_handling(self):
        """Test error handling in dispatch."""
        dispatcher = OperatorDispatcher()

        # Test error when no implementation found
        with pytest.raises(TypeError):
            dispatcher.dispatch("nonexistent_op", "unsupported_type")

        # Test error when no arguments provided
        with pytest.raises(ValueError):
            dispatcher.dispatch("add")

    def test_dispatch_cache(self):
        """Test dispatch caching functionality."""
        dispatcher = OperatorDispatcher()

        # First call should populate cache
        result1 = dispatcher.dispatch("add", 1, 2)

        # Second call should use cache
        result2 = dispatcher.dispatch("add", 1, 2)

        assert result1 == result2 == 3

        # Check cache hit information
        info = dispatcher.get_dispatch_info("add", 1, 2)
        assert info["cache_hit"] is True

    def test_get_dispatch_info(self):
        """Test getting dispatch information."""
        dispatcher = OperatorDispatcher()

        info = dispatcher.get_dispatch_info("add", 1, 2)

        assert info["operator_name"] == "add"
        assert info["input_types"] == (int, int)
        assert info["selected_overload"] is not None
        assert info["available_overloads"] > 0
        assert isinstance(info["fallback_chain"], list)

    def test_clear_cache(self):
        """Test clearing dispatch cache."""
        dispatcher = OperatorDispatcher()

        # Populate cache
        dispatcher.dispatch("add", 1, 2)

        # Clear cache
        dispatcher.clear_cache()

        # Check cache is cleared
        info = dispatcher.get_dispatch_info("add", 1, 2)
        assert info["cache_hit"] is False

    def test_error_context_in_implementation(self):
        """Test that implementation errors include context."""
        dispatcher = OperatorDispatcher()

        def failing_implementation(a, b):
            raise ValueError("Test error")

        dispatcher.register_overload(
            "failing_op",
            TypeSignature((int, int)),
            failing_implementation,
            description="Failing operation"
        )

        with pytest.raises(ValueError) as exc_info:
            dispatcher.dispatch("failing_op", 1, 2)

        assert "Failing operation" in str(exc_info.value)
        assert "Test error" in str(exc_info.value)


class TestGlobalDispatcher:
    """Test cases for global dispatcher functions."""

    def test_get_dispatcher(self):
        """Test getting global dispatcher."""
        dispatcher = get_dispatcher()
        assert isinstance(dispatcher, OperatorDispatcher)

    def test_dispatch_operator_function(self):
        """Test global dispatch_operator function."""
        result = dispatch_operator("add", 3, 4)
        assert result == 7

    def test_register_operator_overload_function(self):
        """Test global register_operator_overload function."""
        def test_op(a: str, b: str) -> str:
            return f"{a}_{b}"

        register_operator_overload(
            "test_global_op",
            (str, str),
            test_op,
            description="Test operation"
        )

        result = dispatch_operator("test_global_op", "hello", "world")
        assert result == "hello_world"

    def test_get_operator_overloads_function(self):
        """Test global get_operator_overloads function."""
        overloads = get_operator_overloads("add")
        assert len(overloads) > 0
        assert all(isinstance(o, OperatorOverload) for o in overloads)

    def test_get_dispatch_info_function(self):
        """Test global get_dispatch_info function."""
        info = get_dispatch_info("add", 1, 2)
        assert info["operator_name"] == "add"
        assert info["input_types"] == (int, int)


class TestPolymorphismScenarios:
    """Test complex polymorphism scenarios."""

    def test_multiple_implementations_same_operator(self):
        """Test multiple implementations of the same operator."""
        dispatcher = OperatorDispatcher()

        def numeric_add(a, b):
            return a + b

        def string_add(a, b):
            return f"concat({a},{b})"

        def list_add(a, b):
            return a + b  # List concatenation

        # Register overloads
        dispatcher.register_overload("poly_add", TypeSignature((int, int)), numeric_add)
        dispatcher.register_overload("poly_add", TypeSignature((float, float)), numeric_add)
        dispatcher.register_overload("poly_add", TypeSignature((str, str)), string_add)
        dispatcher.register_overload("poly_add", TypeSignature((list, list)), list_add)

        # Test different type combinations
        assert dispatcher.dispatch("poly_add", 1, 2) == 3
        assert dispatcher.dispatch("poly_add", 1.5, 2.5) == 4.0
        assert dispatcher.dispatch("poly_add", "a", "b") == "concat(a,b)"
        assert dispatcher.dispatch("poly_add", [1, 2], [3, 4]) == [1, 2, 3, 4]

    def test_inheritance_based_dispatch(self):
        """Test dispatch based on inheritance hierarchies."""
        dispatcher = OperatorDispatcher()

        class Animal:
            def __init__(self, name):
                self.name = name

        class Dog(Animal):
            pass

        class Cat(Animal):
            pass

        def animal_greet(a, b):
            return f"{a.name} meets {b.name}"

        def dog_greet(a, b):
            return f"{a.name} barks at {b.name}"

        # Register overloads
        dispatcher.register_overload("greet", TypeSignature((Animal, Animal)), animal_greet, priority=1)
        dispatcher.register_overload("greet", TypeSignature((Dog, Dog)), dog_greet, priority=2)

        dog1 = Dog("Rex")
        dog2 = Dog("Buddy")
        cat1 = Cat("Whiskers")

        # Dog-Dog should use specific handler
        result = dispatcher.dispatch("greet", dog1, dog2)
        assert "barks at" in result

        # Dog-Cat should use general handler
        result = dispatcher.dispatch("greet", dog1, cat1)
        assert "meets" in result

    def test_fallback_with_type_coercion(self):
        """Test fallback mechanisms with type coercion."""
        dispatcher = OperatorDispatcher()

        def int_operation(a, b):
            return int(a) + int(b)

        # Only register int handler
        dispatcher.register_overload("coerce_add", TypeSignature((int, int)), int_operation)

        # Register fallback chain to try coercion
        def coercion_fallback(a, b):
            try:
                return dispatcher.dispatch("coerce_add", int(a), int(b))
            except (ValueError, TypeError):
                raise TypeError(f"Cannot coerce {type(a)} and {type(b)} to int")

        dispatcher.register_overload(
            "coerce_fallback",
            TypeSignature((Any, Any)),
            coercion_fallback,
            priority=1
        )
        dispatcher.register_fallback_chain("coerce_add", ["coerce_fallback"])

        # Test that string numbers get coerced
        result = dispatcher.dispatch("coerce_add", "10", "20")
        assert result == 30

    def test_complex_numpy_dispatch(self):
        """Test complex dispatch scenarios with NumPy arrays."""
        dispatcher = OperatorDispatcher()

        def array_array_op(a, b):
            return np.multiply(a, b)

        def array_scalar_op(a, b):
            if isinstance(a, np.ndarray):
                return a * b
            return b * a

        def scalar_array_op(a, b):
            return a * b

        # Register overloads
        dispatcher.register_overload("complex_mul", TypeSignature((np.ndarray, np.ndarray)), array_array_op, priority=10)
        dispatcher.register_overload("complex_mul", TypeSignature((np.ndarray, (int, float))), array_scalar_op, priority=9)
        dispatcher.register_overload("complex_mul", TypeSignature(((int, float), np.ndarray)), scalar_array_op, priority=9)

        arr = np.array([1, 2, 3])

        # Array-array
        result = dispatcher.dispatch("complex_mul", arr, arr)
        np.testing.assert_array_equal(result, [1, 4, 9])

        # Array-scalar
        result = dispatcher.dispatch("complex_mul", arr, 2)
        np.testing.assert_array_equal(result, [2, 4, 6])

        # Scalar-array
        result = dispatcher.dispatch("complex_mul", 3, arr)
        np.testing.assert_array_equal(result, [3, 6, 9])


class TestPerformanceAndEdgeCases:
    """Test performance characteristics and edge cases."""

    def test_large_number_of_overloads(self):
        """Test performance with many overloads."""
        dispatcher = OperatorDispatcher()

        # Register many overloads
        for i in range(100):
            def handler(a, b, i=i):
                return f"handler_{i}"

            dispatcher.register_overload(
                "many_overloads",
                TypeSignature((str, str)),
                handler,
                priority=i,
                description=f"Handler {i}"
            )

        # Should still work and select highest priority
        result = dispatcher.dispatch("many_overloads", "a", "b")
        assert result == "handler_99"

    def test_recursive_fallback_protection(self):
        """Test protection against infinite recursion in fallbacks."""
        dispatcher = OperatorDispatcher()

        # Create circular fallback chain (should not cause infinite recursion)
        dispatcher.register_fallback_chain("op_a", ["op_b"])
        dispatcher.register_fallback_chain("op_b", ["op_c"])
        dispatcher.register_fallback_chain("op_c", ["op_a"])

        # Should eventually give up and raise error
        with pytest.raises(TypeError):
            dispatcher.dispatch("op_a", "test")

    def test_thread_safety_basics(self):
        """Basic test for thread safety (dispatch cache)."""
        dispatcher = OperatorDispatcher()

        # This is a basic test - full thread safety testing would require
        # concurrent execution, which is complex to test reliably

        # Multiple dispatches should not interfere
        result1 = dispatcher.dispatch("add", 1, 2)
        result2 = dispatcher.dispatch("add", 3, 4)
        result3 = dispatcher.dispatch("add", 1, 2)  # Cache hit

        assert result1 == 3
        assert result2 == 7
        assert result3 == 3