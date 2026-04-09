#!/usr/bin/env python3
"""Basic test for display module functionality."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import directly without going through __init__
from earthsci_toolkit.types import ExprNode
from earthsci_toolkit.display import to_unicode, to_latex

def test_basic_functionality():
    """Test basic functionality of display module."""
    print("Testing basic display functionality...")

    # Test chemical subscripts
    print("\n=== Chemical Subscripts ===")
    test_cases = [
        ("O3", "O₃", "\\mathrm{O_3}"),
        ("NO2", "NO₂", "\\mathrm{NO_2}"),
        ("H2O", "H₂O", "\\mathrm{H_2O}"),
        ("CO2", "CO₂", "\\mathrm{CO_2}"),
    ]

    for input_str, expected_unicode, expected_latex in test_cases:
        unicode_result = to_unicode(input_str)
        latex_result = to_latex(input_str)

        print(f"Input: {input_str}")
        print(f"  Unicode: {unicode_result} (expected: {expected_unicode}) {'✓' if unicode_result == expected_unicode else '✗'}")
        print(f"  LaTeX:   {latex_result} (expected: {expected_latex}) {'✓' if latex_result == expected_latex else '✗'}")

    # Test numbers
    print("\n=== Numbers ===")
    number_tests = [
        (42, "42", "42"),
        (1.8e-12, "1.8×10⁻¹²", "1.8 \\times 10^{-12}"),
    ]

    for num, expected_unicode, expected_latex in number_tests:
        unicode_result = to_unicode(num)
        latex_result = to_latex(num)

        print(f"Number: {num}")
        print(f"  Unicode: {unicode_result} (expected: {expected_unicode}) {'✓' if unicode_result == expected_unicode else '✗'}")
        print(f"  LaTeX:   {latex_result} (expected: {expected_latex}) {'✓' if latex_result == expected_latex else '✗'}")

    # Test simple expressions
    print("\n=== Simple Expressions ===")

    # Addition: a + b
    expr = ExprNode(op='+', args=['a', 'b'])
    unicode_result = to_unicode(expr)
    latex_result = to_latex(expr)
    print(f"a + b:")
    print(f"  Unicode: {unicode_result} (expected: a + b) {'✓' if unicode_result == 'a + b' else '✗'}")
    print(f"  LaTeX:   {latex_result} (expected: a + b) {'✓' if latex_result == 'a + b' else '✗'}")

    # Multiplication: a * b
    expr = ExprNode(op='*', args=['a', 'b'])
    unicode_result = to_unicode(expr)
    latex_result = to_latex(expr)
    expected_latex_mul = 'a \\cdot b'
    print(f"a * b:")
    print(f"  Unicode: {unicode_result} (expected: a·b) {'✓' if unicode_result == 'a·b' else '✗'}")
    print(f"  LaTeX:   {latex_result} (expected: {expected_latex_mul}) {'✓' if latex_result == expected_latex_mul else '✗'}")

    # Division: a / b
    expr = ExprNode(op='/', args=['a', 'b'])
    unicode_result = to_unicode(expr)
    latex_result = to_latex(expr)
    expected_latex_div = '\\frac{a}{b}'
    print(f"a / b:")
    print(f"  Unicode: {unicode_result} (expected: a/b) {'✓' if unicode_result == 'a/b' else '✗'}")
    print(f"  LaTeX:   {latex_result} (expected: {expected_latex_div}) {'✓' if latex_result == expected_latex_div else '✗'}")

    # Power: x^3
    expr = ExprNode(op='^', args=['x', 3])
    unicode_result = to_unicode(expr)
    latex_result = to_latex(expr)
    expected_latex_pow = 'x^{3}'
    print(f"x^3:")
    print(f"  Unicode: {unicode_result} (expected: x³) {'✓' if unicode_result == 'x³' else '✗'}")
    print(f"  LaTeX:   {latex_result} (expected: {expected_latex_pow}) {'✓' if latex_result == expected_latex_pow else '✗'}")

    # Derivative: D(x) with respect to t
    expr = ExprNode(op='D', args=['x'], wrt='t')
    unicode_result = to_unicode(expr)
    latex_result = to_latex(expr)
    expected_latex_deriv = '\\frac{\\partial x}{\\partial t}'
    print(f"D(x)/Dt:")
    print(f"  Unicode: {unicode_result} (expected: ∂x/∂t) {'✓' if unicode_result == '∂x/∂t' else '✗'}")
    print(f"  LaTeX:   {latex_result} (expected: {expected_latex_deriv}) {'✓' if latex_result == expected_latex_deriv else '✗'}")

    print("\n=== Test Complete ===")

if __name__ == '__main__':
    test_basic_functionality()