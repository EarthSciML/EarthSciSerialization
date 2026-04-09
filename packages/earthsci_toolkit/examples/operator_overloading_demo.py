#!/usr/bin/env python3
"""
Demonstration of the ESM Format operator overloading and polymorphism system.

This example shows how to use type-based operator dispatch, register custom
operator implementations, and leverage fallback mechanisms.
"""

import numpy as np
from typing import Any
import sys
import os

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from earthsci_toolkit.operator_dispatch import (
    get_dispatcher,
    dispatch_operator,
    register_operator_overload,
    get_dispatch_info
)


def demonstrate_basic_dispatch():
    """Demonstrate basic operator dispatch with built-in overloads."""
    print("=== Basic Operator Dispatch ===")

    # Integer arithmetic
    result = dispatch_operator("add", 5, 3)
    print(f"dispatch_operator('add', 5, 3) = {result}")

    # Float arithmetic
    result = dispatch_operator("add", 5.5, 3.2)
    print(f"dispatch_operator('add', 5.5, 3.2) = {result}")

    # Mixed types
    result = dispatch_operator("add", 5, 3.2)
    print(f"dispatch_operator('add', 5, 3.2) = {result}")

    # Array operations
    a = np.array([1, 2, 3])
    b = np.array([4, 5, 6])
    result = dispatch_operator("add", a, b)
    print(f"dispatch_operator('add', array([1,2,3]), array([4,5,6])) = {result}")

    # Array-scalar operations
    result = dispatch_operator("add", a, 10)
    print(f"dispatch_operator('add', array([1,2,3]), 10) = {result}")

    print()


def demonstrate_custom_overloads():
    """Demonstrate registering custom operator overloads."""
    print("=== Custom Operator Overloads ===")

    # String concatenation
    def string_concat(a: str, b: str) -> str:
        return f"{a}+{b}"

    register_operator_overload(
        "add",
        (str, str),
        string_concat,
        priority=10,
        description="String concatenation with + separator"
    )

    result = dispatch_operator("add", "hello", "world")
    print(f"dispatch_operator('add', 'hello', 'world') = '{result}'")

    # List concatenation
    def list_concat(a: list, b: list) -> list:
        return a + b

    register_operator_overload(
        "add",
        (list, list),
        list_concat,
        priority=10,
        description="List concatenation"
    )

    result = dispatch_operator("add", [1, 2], [3, 4])
    print(f"dispatch_operator('add', [1,2], [3,4]) = {result}")

    # Dictionary merging
    def dict_merge(a: dict, b: dict) -> dict:
        result = a.copy()
        result.update(b)
        return result

    register_operator_overload(
        "add",
        (dict, dict),
        dict_merge,
        priority=10,
        description="Dictionary merging"
    )

    result = dispatch_operator("add", {"a": 1}, {"b": 2})
    print(f"dispatch_operator('add', {{'a': 1}}, {{'b': 2}}) = {result}")

    print()


def demonstrate_polymorphism():
    """Demonstrate polymorphism with different implementations."""
    print("=== Polymorphism Example ===")

    # Define custom classes with inheritance
    class Shape:
        def __init__(self, name):
            self.name = name

    class Rectangle(Shape):
        def __init__(self, width, height):
            super().__init__("Rectangle")
            self.width = width
            self.height = height

    class Circle(Shape):
        def __init__(self, radius):
            super().__init__("Circle")
            self.radius = radius

    # General shape combination
    def combine_shapes(a: Shape, b: Shape) -> str:
        return f"Combined {a.name} and {b.name}"

    # Specific rectangle combination
    def combine_rectangles(a: Rectangle, b: Rectangle) -> Rectangle:
        return Rectangle(a.width + b.width, a.height + b.height)

    # Specific circle combination
    def combine_circles(a: Circle, b: Circle) -> Circle:
        return Circle(max(a.radius, b.radius))

    # Register overloads with different specificities
    register_operator_overload("combine", (Shape, Shape), combine_shapes, priority=1)
    register_operator_overload("combine", (Rectangle, Rectangle), combine_rectangles, priority=10)
    register_operator_overload("combine", (Circle, Circle), combine_circles, priority=10)

    # Test polymorphic dispatch
    rect1 = Rectangle(10, 5)
    rect2 = Rectangle(3, 7)
    circle1 = Circle(5)
    circle2 = Circle(3)

    # Rectangle + Rectangle -> specific handler
    result = dispatch_operator("combine", rect1, rect2)
    print(f"Rectangle(10,5) + Rectangle(3,7) = Rectangle({result.width},{result.height})")

    # Circle + Circle -> specific handler
    result = dispatch_operator("combine", circle1, circle2)
    print(f"Circle(5) + Circle(3) = Circle({result.radius})")

    # Rectangle + Circle -> general handler
    result = dispatch_operator("combine", rect1, circle1)
    print(f"Rectangle + Circle = '{result}'")

    print()


def demonstrate_fallback_mechanisms():
    """Demonstrate fallback mechanisms."""
    print("=== Fallback Mechanisms ===")

    dispatcher = get_dispatcher()

    # Create a primary operation that only works with specific types
    def strict_multiply(a: int, b: int) -> int:
        return a * b

    register_operator_overload(
        "strict_multiply",
        (int, int),
        strict_multiply,
        priority=10,
        description="Strict integer multiplication"
    )

    # Create a fallback that tries type coercion
    def coercion_multiply(a: Any, b: Any) -> Any:
        try:
            # Try to convert to int
            int_a = int(a)
            int_b = int(b)
            return dispatch_operator("strict_multiply", int_a, int_b)
        except (ValueError, TypeError):
            # If that fails, fall back to regular multiplication
            return a * b

    register_operator_overload(
        "coercion_multiply",
        (Any, Any),
        coercion_multiply,
        priority=5,
        description="Multiplication with type coercion"
    )

    # Register fallback chain
    dispatcher.register_fallback_chain("strict_multiply", ["coercion_multiply"])

    # Test fallback behavior
    print("Testing strict_multiply with different inputs:")

    # Direct int multiplication
    result = dispatch_operator("strict_multiply", 5, 3)
    print(f"strict_multiply(5, 3) = {result}")

    # String numbers (should fall back to coercion)
    result = dispatch_operator("strict_multiply", "5", "3")
    print(f"strict_multiply('5', '3') = {result}")

    # Floats (should fall back to coercion, then regular multiplication)
    result = dispatch_operator("strict_multiply", 5.5, 2.2)
    print(f"strict_multiply(5.5, 2.2) = {result}")

    print()


def demonstrate_dispatch_introspection():
    """Demonstrate introspection of dispatch decisions."""
    print("=== Dispatch Introspection ===")

    # Get dispatch info for different scenarios
    scenarios = [
        ("add", 5, 3),
        ("add", 5.5, 3.2),
        ("add", "hello", "world"),
        ("add", np.array([1, 2]), np.array([3, 4])),
    ]

    for operator_name, *args in scenarios:
        info = get_dispatch_info(operator_name, *args)

        print(f"Dispatch info for {operator_name}{args}:")
        print(f"  Selected overload: {info['selected_overload']['description']}")
        print(f"  Priority: {info['selected_overload']['priority']}")
        print(f"  Specificity: {info['selected_overload']['specificity']}")
        print(f"  Available overloads: {info['available_overloads']}")
        print(f"  Cache hit: {info['cache_hit']}")
        print()


def demonstrate_performance_characteristics():
    """Demonstrate performance characteristics of the dispatch system."""
    print("=== Performance Characteristics ===")

    import time

    # Time dispatch vs direct call
    iterations = 10000

    # Direct Python addition
    start = time.time()
    for _ in range(iterations):
        result = 5 + 3
    direct_time = time.time() - start

    # Dispatched addition
    start = time.time()
    for _ in range(iterations):
        result = dispatch_operator("add", 5, 3)
    dispatch_time = time.time() - start

    print(f"Direct addition ({iterations} iterations): {direct_time:.4f}s")
    print(f"Dispatched addition ({iterations} iterations): {dispatch_time:.4f}s")
    print(f"Overhead: {(dispatch_time / direct_time - 1) * 100:.1f}%")

    # Test cache effectiveness
    dispatcher = get_dispatcher()
    dispatcher.clear_cache()

    # First call (no cache)
    start = time.time()
    result = dispatch_operator("add", 5, 3)
    first_call_time = time.time() - start

    # Second call (cache hit)
    start = time.time()
    result = dispatch_operator("add", 5, 3)
    cached_call_time = time.time() - start

    print(f"First call (cache miss): {first_call_time:.6f}s")
    print(f"Second call (cache hit): {cached_call_time:.6f}s")
    if cached_call_time > 0:
        print(f"Cache speedup: {first_call_time / cached_call_time:.1f}x")

    print()


def main():
    """Run all demonstrations."""
    print("ESM Format Operator Overloading and Polymorphism Demo")
    print("=" * 60)
    print()

    demonstrate_basic_dispatch()
    demonstrate_custom_overloads()
    demonstrate_polymorphism()
    demonstrate_fallback_mechanisms()
    demonstrate_dispatch_introspection()
    demonstrate_performance_characteristics()

    print("Demo completed successfully!")
    print("The operator dispatch system provides:")
    print("- Type-based automatic operator selection")
    print("- Multiple implementations per operator (polymorphism)")
    print("- Priority-based overload resolution")
    print("- Fallback mechanisms for unsupported type combinations")
    print("- Performance optimization through caching")
    print("- Full introspection and debugging capabilities")


if __name__ == "__main__":
    main()