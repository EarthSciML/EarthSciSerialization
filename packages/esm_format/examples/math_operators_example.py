"""
Example demonstrating mathematical operators in ESM Format.

This example shows how to:
1. Use the built-in mathematical operators (add, subtract, multiply, divide)
2. Handle different numeric types and broadcasting
3. Configure precision and error handling
4. Work with numpy arrays and scalar values
"""

import numpy as np
# NOTE: This example relies on operator registry functionality that
# is not currently implemented in the ESM format specification.
# OperatorType has been removed as it's not part of the spec.

from esm_format import (
    Operator,
    # Registry functionality not implemented
)


def main():
    """Demonstrate mathematical operators functionality."""

    print("=== ESM Format Mathematical Operators Example ===\n")

    # 1. List available mathematical operators
    print("1. Available mathematical operators:")
    registry = get_registry()
    math_operators = list_operators_by_type(OperatorType.ARITHMETIC)
    print(f"   Mathematical operators: {math_operators}\n")

    # 2. Create operator instances
    print("2. Creating mathematical operator instances...")

    # Create addition operator with default settings
    add_op = create_operator_by_name(
        name="add",
        operator_type=OperatorType.ARITHMETIC,
        parameters={},
        input_variables=["a", "b"],
        output_variables=["sum"]
    )

    # Create division operator with custom precision
    div_op = create_operator_by_name(
        name="divide",
        operator_type=OperatorType.ARITHMETIC,
        parameters={
            "precision": "single",
            "nan_handling": "warn"
        },
        input_variables=["numerator", "denominator"],
        output_variables=["quotient"]
    )

    print(f"   Created: {add_op}")
    print(f"   Created: {div_op}")

    # 3. Demonstrate scalar operations
    print("\n3. Scalar operations:")

    # Basic addition
    result = add_op.evaluate(5, 3)
    print(f"   5 + 3 = {result}")

    # Chain addition
    result = add_op.evaluate(1, 2, 3, 4)
    print(f"   1 + 2 + 3 + 4 = {result}")

    # Multiplication with floats
    mul_op = create_operator_by_name("multiply", OperatorType.ARITHMETIC)
    result = mul_op.evaluate(2.5, 4.0)
    print(f"   2.5 * 4.0 = {result}")

    # Division with precision handling
    result = div_op.evaluate(10.0, 3.0)
    print(f"   10.0 / 3.0 = {result} (single precision)")

    # 4. Demonstrate array operations with broadcasting
    print("\n4. Array operations with broadcasting:")

    # Create arrays
    arr1 = np.array([1, 2, 3, 4])
    arr2 = np.array([10, 20, 30, 40])
    scalar = 5

    # Array addition
    result = add_op.evaluate(arr1, arr2)
    print(f"   {arr1} + {arr2} = {result}")

    # Broadcasting: array + scalar
    result = add_op.evaluate(arr1, scalar)
    print(f"   {arr1} + {scalar} = {result}")

    # Matrix operations
    matrix1 = np.array([[1, 2], [3, 4]])
    matrix2 = np.array([[5, 6], [7, 8]])

    result = mul_op.evaluate(matrix1, matrix2)
    print(f"   Matrix element-wise multiplication:")
    print(f"   {matrix1}")
    print(f"   * {matrix2}")
    print(f"   = {result}")

    # 5. Demonstrate precision and error handling
    print("\n5. Precision and error handling:")

    # Create high-precision operator
    high_precision_div = create_operator_by_name(
        name="divide",
        operator_type=OperatorType.ARITHMETIC,
        parameters={
            "precision": "double",
            "nan_handling": "warn",
            "overflow_handling": "warn"
        }
    )

    # Division by very small number (potential precision issues)
    result = high_precision_div.evaluate(1.0, 1e-10)
    print(f"   1.0 / 1e-10 = {result}")

    # Division by zero (should warn)
    print("   Testing division by zero (should produce warning):")
    result = div_op.evaluate(5.0, 0.0)
    print(f"   5.0 / 0.0 = {result}")

    # 6. Demonstrate type conversion
    print("\n6. Type conversion and validation:")

    # String to number conversion
    try:
        result = add_op.evaluate("5.5", "2.3")
        print(f"   '5.5' + '2.3' = {result}")
    except Exception as e:
        print(f"   String conversion error: {e}")

    # List to array conversion
    try:
        result = mul_op.evaluate([1, 2, 3], [2, 3, 4])
        print(f"   [1,2,3] * [2,3,4] = {result}")
    except Exception as e:
        print(f"   List conversion error: {e}")

    # Invalid type handling
    try:
        result = add_op.evaluate("invalid", 5)
        print(f"   Invalid conversion result: {result}")
    except Exception as e:
        print(f"   ✓ Properly caught invalid type: {type(e).__name__}")

    # 7. Demonstrate all four basic operations
    print("\n7. Complete arithmetic operations:")

    a, b = 12.0, 4.0

    sub_op = create_operator_by_name("subtract", OperatorType.ARITHMETIC)

    print(f"   a = {a}, b = {b}")
    print(f"   a + b = {add_op.evaluate(a, b)}")
    print(f"   a - b = {sub_op.evaluate(a, b)}")
    print(f"   a * b = {mul_op.evaluate(a, b)}")
    print(f"   a / b = {div_op.evaluate(a, b)}")

    # 8. Complex expression evaluation (simulating expression tree)
    print("\n8. Complex expression evaluation:")
    print("   Evaluating: (2 + 3) * 4 / (6 - 4)")

    # Step by step
    step1 = add_op.evaluate(2, 3)        # 2 + 3 = 5
    step2 = mul_op.evaluate(step1, 4)    # 5 * 4 = 20
    step3 = sub_op.evaluate(6, 4)        # 6 - 4 = 2
    result = div_op.evaluate(step2, step3)  # 20 / 2 = 10

    print(f"   Step 1: 2 + 3 = {step1}")
    print(f"   Step 2: {step1} * 4 = {step2}")
    print(f"   Step 3: 6 - 4 = {step3}")
    print(f"   Final: {step2} / {step3} = {result}")

    print("\n=== Mathematical Operators Example Completed Successfully! ===")


if __name__ == "__main__":
    main()