#!/usr/bin/env python3
"""
Quick test of the SymPy bridge functions.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from earthsci_toolkit.expression import to_sympy, from_sympy, symbolic_jacobian
from earthsci_toolkit.types import ExprNode, Model, ModelVariable, Equation
import sympy as sp


def test_basic_conversions():
    """Test basic to_sympy and from_sympy conversions."""
    print("Testing basic conversions...")

    # Test numbers
    assert to_sympy(5) == 5
    assert from_sympy(sp.sympify(5)) == 5.0

    # Test variables
    x_sympy = to_sympy("x")
    assert isinstance(x_sympy, sp.Symbol)
    assert str(x_sympy) == "x"
    assert from_sympy(x_sympy) == "x"

    # Test simple operations
    expr = ExprNode(op="+", args=[2, "x"])
    sympy_expr = to_sympy(expr)
    print(f"ESM: 2 + x -> SymPy: {sympy_expr}")
    back_to_esm = from_sympy(sympy_expr)
    print(f"SymPy: {sympy_expr} -> ESM: {back_to_esm}")

    # Test multiplication
    expr = ExprNode(op="*", args=["x", "y"])
    sympy_expr = to_sympy(expr)
    print(f"ESM: x * y -> SymPy: {sympy_expr}")

    # Test exponential
    expr = ExprNode(op="exp", args=["x"])
    sympy_expr = to_sympy(expr)
    print(f"ESM: exp(x) -> SymPy: {sympy_expr}")

    # Test power
    expr = ExprNode(op="^", args=["x", 2])
    sympy_expr = to_sympy(expr)
    print(f"ESM: x^2 -> SymPy: {sympy_expr}")

    print("Basic conversions: PASSED\n")


def test_derivative_operations():
    """Test derivative operations."""
    print("Testing derivative operations...")

    # Test derivative
    expr = ExprNode(op="D", args=["x"], wrt="t")
    sympy_expr = to_sympy(expr)
    print(f"ESM: D(x, t) -> SymPy: {sympy_expr}")

    back_to_esm = from_sympy(sympy_expr)
    print(f"SymPy: {sympy_expr} -> ESM: {back_to_esm}")

    print("Derivative operations: PASSED\n")


def test_symbolic_jacobian():
    """Test symbolic Jacobian computation."""
    print("Testing symbolic Jacobian...")

    # Create a simple model with state variables and equations
    # dx/dt = -kx
    # dy/dt = kx - ly

    model = Model(
        name="test_model",
        variables={
            "x": ModelVariable(type="state"),
            "y": ModelVariable(type="state"),
            "k": ModelVariable(type="parameter"),
            "l": ModelVariable(type="parameter")
        },
        equations=[
            Equation(
                lhs=ExprNode(op="D", args=["x"], wrt="t"),
                rhs=ExprNode(op="*", args=[-1, ExprNode(op="*", args=["k", "x"])])
            ),
            Equation(
                lhs=ExprNode(op="D", args=["y"], wrt="t"),
                rhs=ExprNode(op="-", args=[
                    ExprNode(op="*", args=["k", "x"]),
                    ExprNode(op="*", args=["l", "y"])
                ])
            )
        ]
    )

    jacobian = symbolic_jacobian(model)
    print(f"Jacobian matrix:\n{jacobian}")

    # Expected Jacobian should be:
    # [[-k,  0],
    #  [ k, -l]]
    expected_shape = (2, 2)
    assert jacobian.shape == expected_shape, f"Expected shape {expected_shape}, got {jacobian.shape}"

    print("Symbolic Jacobian: PASSED\n")


if __name__ == "__main__":
    print("Testing SymPy bridge functions...\n")

    try:
        test_basic_conversions()
        test_derivative_operations()
        test_symbolic_jacobian()
        print("All tests PASSED!")
    except Exception as e:
        print(f"Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)