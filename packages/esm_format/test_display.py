#!/usr/bin/env python3
"""Test for display module functionality."""

from display_test import to_unicode, to_latex, ExprNode, Equation

def test_display():
    """Test display functionality."""
    print("Testing display module...")

    # Test strings (chemical formulas)
    print("\n=== Chemical Subscripts ===")
    test_cases = [
        ("O3", "O₃", "\\mathrm{O_3}"),
        ("NO2", "NO₂", "\\mathrm{NO_2}"),
        ("H2O", "H₂O", "\\mathrm{H_2O}"),
        ("CO2", "CO₂", "\\mathrm{CO_2}"),
        ("Ca2", "Ca₂", "\\mathrm{Ca_2}"),
    ]

    all_passed = True
    for formula, expected_unicode, expected_latex in test_cases:
        unicode_result = to_unicode(formula)
        latex_result = to_latex(formula)

        unicode_pass = unicode_result == expected_unicode
        latex_pass = latex_result == expected_latex

        if not unicode_pass or not latex_pass:
            all_passed = False

        print(f"{formula}:")
        print(f"  Unicode: {unicode_result} {'✓' if unicode_pass else '✗ (expected: ' + expected_unicode + ')'}")
        print(f"  LaTeX:   {latex_result} {'✓' if latex_pass else '✗ (expected: ' + expected_latex + ')'}")

    # Test numbers
    print("\n=== Numbers ===")
    number_tests = [
        (42, "42", "42"),
        (1.8e-12, "1.8×10⁻¹²", "1.8 \\times 10^{-12}"),
    ]

    for num, expected_unicode, expected_latex in number_tests:
        unicode_result = to_unicode(num)
        latex_result = to_latex(num)

        unicode_pass = unicode_result == expected_unicode
        latex_pass = latex_result == expected_latex

        if not unicode_pass or not latex_pass:
            all_passed = False

        print(f"{num}:")
        print(f"  Unicode: {unicode_result} {'✓' if unicode_pass else '✗ (expected: ' + expected_unicode + ')'}")
        print(f"  LaTeX:   {latex_result} {'✓' if latex_pass else '✗ (expected: ' + expected_latex + ')'}")

    # Test expressions
    print("\n=== Expressions ===")
    expression_tests = [
        (ExprNode(op='+', args=['a', 'b']), "a + b", "a + b"),
        (ExprNode(op='*', args=['a', 'b']), "a·b", "a \\cdot b"),
        (ExprNode(op='/', args=['a', 'b']), "a/b", "\\frac{a}{b}"),
        (ExprNode(op='^', args=['x', 3]), "x³", "x^{3}"),
        (ExprNode(op='D', args=['x'], wrt='t'), "∂x/∂t", "\\frac{\\partial x}{\\partial t}"),
        (ExprNode(op='-', args=['a', 'b']), "a − b", "a - b"),
        (ExprNode(op='sqrt', args=['x']), "√x", "\\sqrt{x}"),
        (ExprNode(op='sin', args=['x']), "sin(x)", "\\sin\\left(x\\right)"),
    ]

    for expr, expected_unicode, expected_latex in expression_tests:
        unicode_result = to_unicode(expr)
        latex_result = to_latex(expr)

        unicode_pass = unicode_result == expected_unicode
        latex_pass = latex_result == expected_latex

        if not unicode_pass or not latex_pass:
            all_passed = False

        print(f"{expr.op} expression:")
        print(f"  Unicode: {unicode_result} {'✓' if unicode_pass else '✗ (expected: ' + expected_unicode + ')'}")
        print(f"  LaTeX:   {latex_result} {'✓' if latex_pass else '✗ (expected: ' + expected_latex + ')'}")

    # Test equations
    print("\n=== Equations ===")
    eq = Equation(lhs='x', rhs=ExprNode(op='+', args=['y', 'z']))
    unicode_result = to_unicode(eq)
    latex_result = to_latex(eq)
    print(f"Equation x = y + z:")
    print(f"  Unicode: {unicode_result}")
    print(f"  LaTeX:   {latex_result}")

    print(f"\n=== Test Summary ===")
    if all_passed:
        print("✓ All tests passed!")
        return True
    else:
        print("✗ Some tests failed!")
        return False

if __name__ == '__main__':
    success = test_display()
    exit(0 if success else 1)