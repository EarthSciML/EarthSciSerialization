#!/usr/bin/env python3
"""Simple test for display module functionality."""

import sys
import os

# Add the src directory to the Python path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

# Now import with a different alias to avoid name collision
from earthsci_toolkit import types as esm_types
from earthsci_toolkit import display

def test_simple():
    """Test simple display functionality."""
    print("Testing display functions...")

    # Test chemical subscripts
    test_cases = [
        ("O3", "O₃"),
        ("NO2", "NO₂"),
        ("H2O", "H₂O"),
        ("CO2", "CO₂"),
    ]

    print("\n=== Chemical Subscripts ===")
    for formula, expected in test_cases:
        result = display.to_unicode(formula)
        status = "✓" if result == expected else "✗"
        print(f"{formula} → {result} (expected {expected}) {status}")

    # Test numbers
    print("\n=== Numbers ===")
    result = display.to_unicode(42)
    print(f"42 → {result}")

    result = display.to_unicode(1.8e-12)
    print(f"1.8e-12 → {result}")

    # Test simple expressions
    print("\n=== Expressions ===")
    expr = esm_types.ExprNode(op='+', args=['a', 'b'])
    result = display.to_unicode(expr)
    print(f"a + b → {result}")

    expr = esm_types.ExprNode(op='*', args=['a', 'b'])
    result = display.to_unicode(expr)
    print(f"a * b → {result}")

    expr = esm_types.ExprNode(op='^', args=['x', 3])
    result = display.to_unicode(expr)
    print(f"x^3 → {result}")

    print("\nTesting LaTeX output...")
    result = display.to_latex("O3")
    print(f"LaTeX O3 → {result}")

    expr = esm_types.ExprNode(op='/', args=['a', 'b'])
    result = display.to_latex(expr)
    print(f"LaTeX a/b → {result}")

    print("\nTest completed!")

if __name__ == '__main__':
    test_simple()