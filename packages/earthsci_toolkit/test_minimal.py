#!/usr/bin/env python3
"""Minimal test for display module functionality."""

# Create a minimal ExprNode class for testing
from dataclasses import dataclass, field
from typing import List, Union, Optional

@dataclass
class ExprNode:
    """A node in an expression tree."""
    op: str
    args: List[Union[int, float, str, 'ExprNode']] = field(default_factory=list)
    wrt: Optional[str] = None  # with respect to (for derivatives)
    dim: Optional[str] = None  # dimension information

# Now test the display functions directly
import sys
import os

# Add the src/earthsci_toolkit directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'earthsci_toolkit'))

# Import the display module directly
from display import to_unicode, to_latex

def test_minimal():
    """Test minimal display functionality."""
    print("Testing display module...")

    # Test strings (chemical formulas)
    print("\n=== Chemical Subscripts ===")
    formulas = ["O3", "NO2", "H2O", "CO2"]
    for formula in formulas:
        unicode_result = to_unicode(formula)
        latex_result = to_latex(formula)
        print(f"{formula}:")
        print(f"  Unicode: {unicode_result}")
        print(f"  LaTeX:   {latex_result}")

    # Test numbers
    print("\n=== Numbers ===")
    numbers = [42, 3.14, 1.8e-12]
    for num in numbers:
        unicode_result = to_unicode(num)
        latex_result = to_latex(num)
        print(f"{num}:")
        print(f"  Unicode: {unicode_result}")
        print(f"  LaTeX:   {latex_result}")

    # Test expressions
    print("\n=== Expressions ===")

    # Addition: a + b
    expr = ExprNode(op='+', args=['a', 'b'])
    print("a + b:")
    print(f"  Unicode: {to_unicode(expr)}")
    print(f"  LaTeX:   {to_latex(expr)}")

    # Multiplication: a * b
    expr = ExprNode(op='*', args=['a', 'b'])
    print("a * b:")
    print(f"  Unicode: {to_unicode(expr)}")
    print(f"  LaTeX:   {to_latex(expr)}")

    # Division: a / b
    expr = ExprNode(op='/', args=['a', 'b'])
    print("a / b:")
    print(f"  Unicode: {to_unicode(expr)}")
    print(f"  LaTeX:   {to_latex(expr)}")

    # Power: x^3
    expr = ExprNode(op='^', args=['x', 3])
    print("x^3:")
    print(f"  Unicode: {to_unicode(expr)}")
    print(f"  LaTeX:   {to_latex(expr)}")

    # Derivative: D(x)/Dt
    expr = ExprNode(op='D', args=['x'], wrt='t')
    print("D(x)/Dt:")
    print(f"  Unicode: {to_unicode(expr)}")
    print(f"  LaTeX:   {to_latex(expr)}")

    print("\nTest completed!")

if __name__ == '__main__':
    test_minimal()