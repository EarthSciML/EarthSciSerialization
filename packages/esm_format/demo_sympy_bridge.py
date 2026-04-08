#!/usr/bin/env python3
"""
Demonstration of the SymPy bridge functionality.

This script demonstrates all the features specified in the task:
1. to_sympy(expr: Expr) → sympy.Expr — convert ESM AST to SymPy expression
2. from_sympy(sympy_expr) → Expr — reverse conversion
3. symbolic_jacobian(model: Model) → sympy.Matrix — Jacobian of the ODE system

Mapping includes:
- VarExpr → Symbol or Function(name)(t) for state vars
- NumExpr → number
- OpExpr('+') → Add
- OpExpr('D',wrt='t') → Derivative(f(t),t)
- OpExpr('exp') → exp
- OpExpr('Pre') → Function('Pre')
- OpExpr('ifelse') → Piecewise
- OpExpr('^') → Pow
- OpExpr('grad') → Derivative
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from esm_format.expression import to_sympy, from_sympy, symbolic_jacobian
from esm_format.types import ExprNode, Model, ModelVariable, Equation
import sympy as sp


def demo_basic_mapping():
    """Demonstrate basic expression mapping."""
    print("=== BASIC EXPRESSION MAPPING ===")

    # VarExpr → Symbol
    print("\n1. Variable expressions to Symbols:")
    var_x = "x"
    sympy_x = to_sympy(var_x)
    print(f"   ESM: {var_x} → SymPy: {sympy_x} (type: {type(sympy_x).__name__})")

    # NumExpr → number
    print("\n2. Number expressions:")
    num = 3.14
    sympy_num = to_sympy(num)
    print(f"   ESM: {num} → SymPy: {sympy_num} (type: {type(sympy_num).__name__})")

    # OpExpr('+') → Add
    print("\n3. Addition operation:")
    add_expr = ExprNode(op="+", args=[2, "x", "y"])
    sympy_add = to_sympy(add_expr)
    print(f"   ESM: 2 + x + y → SymPy: {sympy_add}")

    # OpExpr('^') → Pow
    print("\n4. Power operation:")
    pow_expr = ExprNode(op="^", args=["x", 2])
    sympy_pow = to_sympy(pow_expr)
    print(f"   ESM: x^2 → SymPy: {sympy_pow}")

    # OpExpr('exp') → exp
    print("\n5. Exponential function:")
    exp_expr = ExprNode(op="exp", args=["x"])
    sympy_exp = to_sympy(exp_expr)
    print(f"   ESM: exp(x) → SymPy: {sympy_exp}")


def demo_advanced_operations():
    """Demonstrate advanced operations."""
    print("\n=== ADVANCED OPERATIONS ===")

    # OpExpr('D',wrt='t') → Derivative(f(t),t)
    print("\n1. Derivative operation:")
    deriv_expr = ExprNode(op="D", args=["x"], wrt="t")
    sympy_deriv = to_sympy(deriv_expr)
    print(f"   ESM: D(x, t) → SymPy: {sympy_deriv}")

    # OpExpr('Pre') → Function('Pre')
    print("\n2. Previous value operator:")
    pre_expr = ExprNode(op="Pre", args=["x"])
    sympy_pre = to_sympy(pre_expr)
    print(f"   ESM: Pre(x) → SymPy: {sympy_pre}")

    # OpExpr('ifelse') → Piecewise
    print("\n3. Conditional expression:")
    # For demonstration, using a simple condition
    ifelse_expr = ExprNode(op="ifelse", args=["condition", 1, 0])
    sympy_ifelse = to_sympy(ifelse_expr)
    print(f"   ESM: ifelse(condition, 1, 0) → SymPy: {sympy_ifelse}")

    # OpExpr('grad') → Derivative
    print("\n4. Gradient operation:")
    grad_expr = ExprNode(op="grad", args=["f"], dim="x")
    sympy_grad = to_sympy(grad_expr)
    print(f"   ESM: grad(f, x) → SymPy: {sympy_grad}")


def demo_round_trip():
    """Demonstrate round-trip conversion."""
    print("\n=== ROUND-TRIP CONVERSION ===")

    # Create a complex expression
    complex_expr = ExprNode(op="+", args=[
        ExprNode(op="*", args=[2, ExprNode(op="exp", args=["x"])]),
        ExprNode(op="^", args=["y", 3]),
        1
    ])

    print(f"\n1. Original ESM expression: {complex_expr}")

    # Convert to SymPy
    sympy_expr = to_sympy(complex_expr)
    print(f"2. Converted to SymPy: {sympy_expr}")

    # Convert back to ESM
    back_to_esm = from_sympy(sympy_expr)
    print(f"3. Converted back to ESM: {back_to_esm}")

    # Test simplification through SymPy
    simplified_sympy = sp.simplify(sympy_expr)
    print(f"4. SymPy simplified: {simplified_sympy}")

    simplified_esm = from_sympy(simplified_sympy)
    print(f"5. Simplified back to ESM: {simplified_esm}")


def demo_symbolic_jacobian():
    """Demonstrate symbolic Jacobian computation."""
    print("\n=== SYMBOLIC JACOBIAN ===")

    # Create a model representing a chemical reaction system
    # A → B (rate k1*A)
    # B → C (rate k2*B)
    # System: dA/dt = -k1*A, dB/dt = k1*A - k2*B, dC/dt = k2*B

    model = Model(
        name="chemical_chain",
        variables={
            "A": ModelVariable(type="state", description="Species A concentration"),
            "B": ModelVariable(type="state", description="Species B concentration"),
            "C": ModelVariable(type="state", description="Species C concentration"),
            "k1": ModelVariable(type="parameter", description="Rate constant A→B"),
            "k2": ModelVariable(type="parameter", description="Rate constant B→C")
        },
        equations=[
            # dA/dt = -k1*A
            Equation(
                lhs=ExprNode(op="D", args=["A"], wrt="t"),
                rhs=ExprNode(op="*", args=[-1, ExprNode(op="*", args=["k1", "A"])])
            ),
            # dB/dt = k1*A - k2*B
            Equation(
                lhs=ExprNode(op="D", args=["B"], wrt="t"),
                rhs=ExprNode(op="-", args=[
                    ExprNode(op="*", args=["k1", "A"]),
                    ExprNode(op="*", args=["k2", "B"])
                ])
            ),
            # dC/dt = k2*B
            Equation(
                lhs=ExprNode(op="D", args=["C"], wrt="t"),
                rhs=ExprNode(op="*", args=["k2", "B"])
            )
        ]
    )

    print(f"\n1. Model: {model.name}")
    print(f"   State variables: {[name for name, var in model.variables.items() if var.type == 'state']}")
    print(f"   Number of equations: {len(model.equations)}")

    # Compute the Jacobian
    jacobian = symbolic_jacobian(model)
    print(f"\n2. Jacobian matrix ({jacobian.shape[0]}×{jacobian.shape[1]}):")
    print(jacobian)

    # Show individual elements
    print("\n3. Jacobian elements:")
    state_vars = ["A", "B", "C"]
    for i, row_var in enumerate(state_vars):
        for j, col_var in enumerate(state_vars):
            element = jacobian[i, j]
            print(f"   ∂(d{row_var}/dt)/∂{col_var} = {element}")


def demo_state_variable_functions():
    """Demonstrate state variables as functions of time."""
    print("\n=== STATE VARIABLES AS FUNCTIONS ===")

    # Create symbols for time-dependent variables
    t = sp.Symbol('t')
    x = sp.Function('x')(t)
    y = sp.Function('y')(t)

    print(f"1. Time-dependent state variables:")
    print(f"   x(t) = {x}")
    print(f"   y(t) = {y}")

    # Create derivatives
    dxdt = sp.Derivative(x, t)
    dydt = sp.Derivative(y, t)

    print(f"\n2. Derivatives:")
    print(f"   dx/dt = {dxdt}")
    print(f"   dy/dt = {dydt}")

    # Show how our conversion handles this
    esm_deriv = ExprNode(op="D", args=["x"], wrt="t")
    sympy_from_esm = to_sympy(esm_deriv)
    print(f"\n3. ESM D(x,t) converts to: {sympy_from_esm}")

    esm_back = from_sympy(dxdt)
    print(f"4. SymPy derivative converts back to: {esm_back}")


if __name__ == "__main__":
    print("SymPy Bridge Demonstration")
    print("=" * 40)

    try:
        demo_basic_mapping()
        demo_advanced_operations()
        demo_round_trip()
        demo_symbolic_jacobian()
        demo_state_variable_functions()

        print("\n" + "=" * 40)
        print("✓ All demonstrations completed successfully!")
        print("\nThe SymPy bridge provides:")
        print("• Bidirectional conversion between ESM and SymPy expressions")
        print("• Support for all required operations (arithmetic, functions, derivatives)")
        print("• Symbolic Jacobian computation for ODE systems")
        print("• Round-trip conversion for symbolic manipulation")
        print("• Integration with SymPy's simplification and analysis tools")

    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)