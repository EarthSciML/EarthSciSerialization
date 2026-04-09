#!/usr/bin/env python3
"""
Test script for the operator registry functionality.

This script tests the custom operator registration system with validation,
documentation requirements, and runtime type checking.
"""

import sys
import traceback
from earthsci_toolkit import (
    register_operator,
    has_operator,
    create_operator,
    create_operator_by_name,
    get_operator_registry,
    get_operator_info,
    list_all_operators,
    Operator,
    OperatorRegistryError,
    OperatorValidationError,
)


# Define test operator classes
class LinearInterpolationOperator:
    """Example linear interpolation operator."""

    def __init__(self, config: Operator):
        self.config = config
        self.name = config.operator_id
        self.parameters = config.config or {}

    def interpolate(self, x_values, y_values, x_new):
        """Simple linear interpolation implementation."""
        method = self.parameters.get('method', 'linear')
        print(f"Performing {method} interpolation with {len(x_values)} points")

        # Mock interpolation result
        return [y_values[0] + (x - x_values[0]) * (y_values[-1] - y_values[0]) / (x_values[-1] - x_values[0]) for x in x_new]

    def __str__(self):
        return f"LinearInterpolation(method={self.parameters.get('method', 'linear')})"


class SplineInterpolationOperator:
    """Example spline interpolation operator (newer version)."""

    def __init__(self, config: Operator):
        self.config = config
        self.name = config.operator_id
        self.parameters = config.config or {}

    def interpolate(self, x_values, y_values, x_new):
        """Spline interpolation implementation."""
        order = self.parameters.get('order', 3)
        print(f"Performing spline interpolation with order {order}")

        # Mock spline interpolation result
        return [y_values[i % len(y_values)] for i in range(len(x_new))]

    def __str__(self):
        return f"SplineInterpolation(order={self.parameters.get('order', 3)})"


class ForwardDifferenceOperator:
    """Example differentiation operator."""

    def __init__(self, config: Operator):
        self.config = config
        self.name = config.operator_id
        self.parameters = config.config or {}

    def differentiate(self, x_values, y_values):
        """Forward difference implementation."""
        h = self.parameters.get('step_size', 1.0)
        print(f"Computing forward difference with step size {h}")

        # Mock differentiation result
        return [(y_values[i+1] - y_values[i]) / h for i in range(len(y_values) - 1)]

    def __str__(self):
        return f"ForwardDifference(h={self.parameters.get('step_size', 1.0)})"


class InvalidOperator:
    """Invalid operator that should fail validation."""

    def __init__(self, wrong_param_name):  # Wrong parameter name
        pass


def test_operator_registration():
    """Test operator registration functionality."""
    print("=== Testing Operator Registration ===\n")

    # Test 1: Register operators with different versions
    print("1. Registering operators...")

    try:
        # Register linear interpolation operator (version 1.0)
        register_operator(
            name="interpolation",
            operator_class=LinearInterpolationOperator,
            input_vars=["x", "y"],
            output_vars=["y_interp"],
            parameters={"method": {"type": "str", "default": "linear"}},
            description="Linear interpolation operator",
            version="1.0",
            documentation="Performs linear interpolation between data points"
        )

        # Register spline interpolation operator as version 2.0 of interpolation
        register_operator(
            name="interpolation",
            operator_class=SplineInterpolationOperator,
            input_vars=["x", "y"],
            output_vars=["y_interp"],
            parameters={"order": {"type": "int", "default": 3}},
            description="Spline interpolation operator",
            version="2.0",
            documentation="Performs spline interpolation with configurable order"
        )

        # Register differentiation operator
        register_operator(
            name="forward_diff",
            operator_class=ForwardDifferenceOperator,
            input_vars=["function"],
            output_vars=["derivative"],
            parameters={"step_size": {"type": "float", "default": 1.0}},
            description="Forward difference differentiation",
            version="1.0",
            documentation="Computes numerical derivatives using forward difference"
        )

        print("   ✓ Registered 'interpolation' v1.0 (Linear)")
        print("   ✓ Registered 'interpolation' v2.0 (Spline)")
        print("   ✓ Registered 'forward_diff' v1.0")

    except Exception as e:
        print(f"   ✗ Registration failed: {e}")
        traceback.print_exc()
        return False

    return True


def test_operator_validation():
    """Test operator validation."""
    print("\n=== Testing Operator Validation ===\n")

    # Test invalid operator registration
    try:
        register_operator(
            name="invalid_op",
            operator_class=InvalidOperator,
            input_vars=["input"],
            output_vars=["output"],
            description="Should fail validation"
        )
        print("   ✗ Invalid operator registration should have failed")
        return False
    except OperatorValidationError as e:
        print(f"   ✓ Invalid operator correctly rejected: {e}")
    except Exception as e:
        print(f"   ✗ Unexpected error: {e}")
        return False

    return True


def test_operator_existence():
    """Test operator existence checking."""
    print("\n=== Testing Operator Existence ===\n")

    # Test operator existence
    print("2. Checking operator existence...")
    tests = [
        ("interpolation", None, True),
        ("interpolation", "1.0", True),
        ("interpolation", "2.0", True),
        ("interpolation", "3.0", False),
        ("forward_diff", None, True),
        ("nonexistent", None, False),
    ]

    all_passed = True
    for name, version, expected in tests:
        result = has_operator(name, version)
        status = "✓" if result == expected else "✗"
        version_str = f" v{version}" if version else ""
        print(f"   {status} '{name}{version_str}' exists: {result} (expected {expected})")
        if result != expected:
            all_passed = False

    return all_passed


def test_operator_creation():
    """Test operator instance creation."""
    print("\n=== Testing Operator Creation ===\n")

    # Test 3: Create operator instances using configurations
    print("3. Creating operator instances with configurations...")

    try:
        # Create linear interpolation operator (v1.0)
        linear_config = Operator(
            operator_id="interpolation",
            needed_vars=["x", "y"],
            modifies=["y_interp"],
            config={"method": "linear"}
        )

        linear_op = create_operator(linear_config)
        print(f"   ✓ Created: {linear_op}")

        # Create spline interpolation operator (v2.0)
        registry = get_operator_registry()
        spline_class = registry.get_operator_class("interpolation", "2.0")
        spline_config = Operator(
            operator_id="interpolation",
            needed_vars=["x", "y"],
            modifies=["y_interp"],
            config={"order": 3}
        )
        spline_op = spline_class(spline_config)
        print(f"   ✓ Created: {spline_op}")

    except Exception as e:
        print(f"   ✗ Operator creation failed: {e}")
        traceback.print_exc()
        return False

    return True


def test_operator_creation_by_name():
    """Test operator creation by name."""
    print("\n=== Testing Operator Creation by Name ===\n")

    # Test 4: Create operator instances by name
    print("4. Creating operator instances by name...")

    try:
        # Create differentiation operator
        diff_op = create_operator_by_name(
            name="forward_diff",
            needed_vars=["function"],
            modifies=["derivative"],
            config={"step_size": 0.1},
            description="Test differentiation operator"
        )
        print(f"   ✓ Created: {diff_op}")

    except Exception as e:
        print(f"   ✗ Operator creation by name failed: {e}")
        traceback.print_exc()
        return False

    return True


def test_operator_information():
    """Test operator information retrieval."""
    print("\n=== Testing Operator Information ===\n")

    # Test 5: Get operator information
    print("5. Getting operator information...")

    try:
        interp_info = get_operator_info("interpolation")
        print(f"   Operator: {interp_info['name']}")
        print(f"   Available versions: {interp_info['versions']}")
        print(f"   Default version: {interp_info['default_version']}")
        print(f"   Class: {interp_info['class_name']}")
        print(f"   Description: {interp_info['description']}")
        print(f"   Input vars: {interp_info['input_vars']}")
        print(f"   Output vars: {interp_info['output_vars']}")

    except Exception as e:
        print(f"   ✗ Failed to get operator information: {e}")
        traceback.print_exc()
        return False

    return True


def test_operator_usage():
    """Test operator usage demonstration."""
    print("\n=== Testing Operator Usage ===\n")

    # Test 6: Demonstrate operator usage
    print("6. Demonstrating operator usage...")

    try:
        # Create operators
        linear_op = create_operator_by_name(
            name="interpolation",
            needed_vars=["x", "y"],
            modifies=["y_interp"],
            config={"method": "linear"}
        )

        diff_op = create_operator_by_name(
            name="forward_diff",
            needed_vars=["function"],
            modifies=["derivative"],
            config={"step_size": 0.1}
        )

        # Sample data
        x_data = [0, 1, 2, 3, 4]
        y_data = [0, 1, 4, 9, 16]  # x^2
        x_new = [0.5, 1.5, 2.5]

        print("   Sample data: x =", x_data, ", y =", y_data)
        print("   Interpolation points:", x_new)

        # Use linear interpolation
        print("\n   Using linear interpolation:")
        linear_result = linear_op.interpolate(x_data, y_data, x_new)
        print(f"   Result: {linear_result}")

        # Use differentiation
        print("\n   Using forward difference:")
        diff_result = diff_op.differentiate(x_data, y_data)
        print(f"   Result: {diff_result}")

    except Exception as e:
        print(f"   ✗ Operator usage failed: {e}")
        traceback.print_exc()
        return False

    return True


def test_list_all_operators():
    """Test listing all registered operators."""
    print("\n=== Testing Operator Listing ===\n")

    # Test 7: List all registered operators
    print("7. All registered operators:")

    try:
        all_operators = list_all_operators()
        for name, info in all_operators.items():
            print(f"   {name}: {info['class_name']}")
            if info['versions']:
                print(f"      Versions: {', '.join(info['versions'])}")
            print(f"      Description: {info['description']}")

    except Exception as e:
        print(f"   ✗ Failed to list operators: {e}")
        traceback.print_exc()
        return False

    return True


def main():
    """Run all tests."""
    print("=== ESM Format Operator Registry Test ===\n")

    tests = [
        test_operator_registration,
        test_operator_validation,
        test_operator_existence,
        test_operator_creation,
        test_operator_creation_by_name,
        test_operator_information,
        test_operator_usage,
        test_list_all_operators,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"Test {test_func.__name__} crashed: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n=== Test Summary ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")

    if failed == 0:
        print("\n🎉 All tests passed! Operator registry is working correctly.")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())