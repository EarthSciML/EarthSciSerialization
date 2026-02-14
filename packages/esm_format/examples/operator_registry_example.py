"""
Example demonstrating the operator registry functionality in ESM Format.

This example shows how to:
1. Register custom operators
2. Create operator instances
3. Use operator versioning
4. List available operators
"""

from esm_format import (
    OperatorRegistry,
    get_operator_registry,
    register_operator,
    create_operator,
    create_operator_by_name,
    list_operators_by_type,
    has_operator,
    Operator,
    OperatorType,
)


# Define custom operator implementations
class LinearInterpolationOperator:
    """Example linear interpolation operator."""

    def __init__(self, config: Operator):
        self.config = config
        self.name = config.name
        self.parameters = config.parameters

    def interpolate(self, x_values, y_values, x_new):
        """Simple linear interpolation implementation."""
        # This is a simplified example - in practice, this would use
        # numpy or scipy for actual interpolation
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
        self.name = config.name
        self.parameters = config.parameters

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
        self.name = config.name
        self.parameters = config.parameters

    def differentiate(self, x_values, y_values):
        """Forward difference implementation."""
        h = self.parameters.get('step_size', 1.0)
        print(f"Computing forward difference with step size {h}")

        # Mock differentiation result
        return [(y_values[i+1] - y_values[i]) / h for i in range(len(y_values) - 1)]

    def __str__(self):
        return f"ForwardDifference(h={self.parameters.get('step_size', 1.0)})"


def main():
    """Demonstrate operator registry functionality."""

    print("=== ESM Format Operator Registry Example ===\n")

    # 1. Register operators with different versions
    print("1. Registering operators...")

    # Register linear interpolation operator (version 1.0)
    register_operator(
        name="interpolation",
        operator_type=OperatorType.INTERPOLATION,
        operator_class=LinearInterpolationOperator,
        version="1.0"
    )

    # Register spline interpolation operator as version 2.0 of interpolation
    register_operator(
        name="interpolation",
        operator_type=OperatorType.INTERPOLATION,
        operator_class=SplineInterpolationOperator,
        version="2.0"
    )

    # Register differentiation operator
    register_operator(
        name="forward_diff",
        operator_type=OperatorType.DIFFERENTIATION,
        operator_class=ForwardDifferenceOperator,
        version="1.0"
    )

    print("   ✓ Registered 'interpolation' v1.0 (Linear)")
    print("   ✓ Registered 'interpolation' v2.0 (Spline)")
    print("   ✓ Registered 'forward_diff' v1.0")

    # 2. List available operators
    print("\n2. Listing available operators...")

    # Get the global registry
    registry = get_operator_registry()

    # List operators by type
    interp_ops = list_operators_by_type(OperatorType.INTERPOLATION)
    diff_ops = list_operators_by_type(OperatorType.DIFFERENTIATION)

    print(f"   Interpolation operators: {interp_ops}")
    print(f"   Differentiation operators: {diff_ops}")

    # 3. Check operator existence
    print("\n3. Checking operator existence...")
    print(f"   'interpolation' exists: {has_operator('interpolation')}")
    print(f"   'interpolation' v1.0 exists: {has_operator('interpolation', '1.0')}")
    print(f"   'interpolation' v2.0 exists: {has_operator('interpolation', '2.0')}")
    print(f"   'interpolation' v3.0 exists: {has_operator('interpolation', '3.0')}")
    print(f"   'nonexistent' exists: {has_operator('nonexistent')}")

    # 4. Create operator instances using configurations
    print("\n4. Creating operator instances with configurations...")

    # Create linear interpolation operator (v1.0)
    linear_config = Operator(
        name="interpolation",
        type=OperatorType.INTERPOLATION,
        parameters={"method": "linear"},
        input_variables=["x", "y"],
        output_variables=["y_interp"]
    )

    linear_op = create_operator(linear_config)
    print(f"   Created: {linear_op}")

    # Create spline interpolation operator (v2.0)
    spline_config = Operator(
        name="interpolation",
        type=OperatorType.INTERPOLATION,
        parameters={"order": 3},
        input_variables=["x", "y"],
        output_variables=["y_interp"]
    )

    # Get specific version by accessing the registry directly
    spline_class = registry.get_operator_class("interpolation", "2.0")
    spline_op = spline_class(spline_config)
    print(f"   Created: {spline_op}")

    # 5. Create operator instances by name
    print("\n5. Creating operator instances by name...")

    # Create differentiation operator
    diff_op = create_operator_by_name(
        name="forward_diff",
        operator_type=OperatorType.DIFFERENTIATION,
        parameters={"step_size": 0.1},
        input_variables=["function"],
        output_variables=["derivative"]
    )
    print(f"   Created: {diff_op}")

    # 6. Get operator information
    print("\n6. Getting operator information...")

    interp_info = registry.get_operator_info("interpolation")
    print(f"   Operator: {interp_info['name']}")
    print(f"   Type: {interp_info['type']}")
    print(f"   Available versions: {interp_info['versions']}")
    print(f"   Default version: {interp_info['default_version']}")

    # 7. Demonstrate operator usage
    print("\n7. Demonstrating operator usage...")

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

    # Use spline interpolation
    print("\n   Using spline interpolation:")
    spline_result = spline_op.interpolate(x_data, y_data, x_new)
    print(f"   Result: {spline_result}")

    # Use differentiation
    print("\n   Using forward difference:")
    diff_result = diff_op.differentiate(x_data, y_data)
    print(f"   Result: {diff_result}")

    # 8. List all registered operators
    print("\n8. All registered operators:")
    all_operators = registry.list_all_operators()
    for name, info in all_operators.items():
        print(f"   {name}: {info['class_name']} ({info['type'].value})")
        if info['versions']:
            print(f"      Versions: {', '.join(info['versions'])}")

    print("\n=== Example completed successfully! ===")


if __name__ == "__main__":
    main()