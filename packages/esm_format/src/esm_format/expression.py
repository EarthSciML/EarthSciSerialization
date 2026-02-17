"""
Expression manipulation and analysis functions.
"""

from typing import Dict, Set, Union, Optional, List
from .esm_types import Expr, ExprNode, Model, ReactionSystem, ModelVariable
import sympy as sp


def free_variables(expr: Expr) -> Set[str]:
    """
    Extract all free variables from an expression.

    Args:
        expr: Expression to analyze

    Returns:
        Set of variable names found in the expression
    """
    if isinstance(expr, str):
        # String is a variable name
        return {expr}
    elif isinstance(expr, (int, float)):
        # Numbers have no variables
        return set()
    elif isinstance(expr, ExprNode):
        # Recursively collect variables from all arguments
        variables = set()
        for arg in expr.args:
            variables.update(free_variables(arg))
        return variables
    else:
        # Unknown type, assume no variables
        return set()


def contains(expr: Expr, var_name: str) -> bool:
    """
    Check if an expression contains a specific variable.

    Args:
        expr: Expression to search in
        var_name: Variable name to look for

    Returns:
        True if variable is found, False otherwise
    """
    return var_name in free_variables(expr)


def evaluate(expr: Expr, bindings: Dict[str, float]) -> float:
    """
    Evaluate an expression with given variable bindings.

    Args:
        expr: Expression to evaluate
        bindings: Dictionary mapping variable names to values

    Returns:
        Numerical result of evaluation

    Raises:
        ValueError: If unbound variables are encountered
        TypeError: If unsupported operations are encountered
    """
    if isinstance(expr, (int, float)):
        return float(expr)
    elif isinstance(expr, str):
        if expr in bindings:
            return bindings[expr]
        else:
            raise ValueError(f"Unbound variable: {expr}")
    elif isinstance(expr, ExprNode):
        # Evaluate arguments first
        arg_values = [evaluate(arg, bindings) for arg in expr.args]

        # Apply operation
        if expr.op == "+":
            return sum(arg_values)
        elif expr.op == "-":
            if len(arg_values) == 1:
                return -arg_values[0]
            elif len(arg_values) == 2:
                return arg_values[0] - arg_values[1]
            else:
                raise TypeError(f"Invalid number of arguments for subtraction: {len(arg_values)}")
        elif expr.op == "*":
            result = 1.0
            for value in arg_values:
                result *= value
            return result
        elif expr.op == "/":
            if len(arg_values) != 2:
                raise TypeError(f"Division requires exactly 2 arguments, got {len(arg_values)}")
            if arg_values[1] == 0:
                raise ValueError("Division by zero")
            return arg_values[0] / arg_values[1]
        elif expr.op == "^" or expr.op == "**":
            if len(arg_values) != 2:
                raise TypeError(f"Power requires exactly 2 arguments, got {len(arg_values)}")
            return arg_values[0] ** arg_values[1]
        elif expr.op == "log":
            if len(arg_values) != 1:
                raise TypeError(f"Logarithm requires exactly 1 argument, got {len(arg_values)}")
            if arg_values[0] <= 0:
                raise ValueError("Logarithm of non-positive number")
            import math
            return math.log(arg_values[0])
        elif expr.op == "exp":
            if len(arg_values) != 1:
                raise TypeError(f"Exponential requires exactly 1 argument, got {len(arg_values)}")
            import math
            return math.exp(arg_values[0])
        elif expr.op == "sin":
            if len(arg_values) != 1:
                raise TypeError(f"Sine requires exactly 1 argument, got {len(arg_values)}")
            import math
            return math.sin(arg_values[0])
        elif expr.op == "cos":
            if len(arg_values) != 1:
                raise TypeError(f"Cosine requires exactly 1 argument, got {len(arg_values)}")
            import math
            return math.cos(arg_values[0])
        else:
            raise TypeError(f"Unsupported operation: {expr.op}")
    else:
        raise TypeError(f"Unsupported expression type: {type(expr)}")


def simplify(expr: Expr) -> Expr:
    """
    Simplify an expression by performing constant folding and basic algebraic simplifications.

    Args:
        expr: Expression to simplify

    Returns:
        Simplified expression
    """
    if isinstance(expr, (int, float, str)):
        # Atomic expressions don't need simplification
        return expr
    elif isinstance(expr, ExprNode):
        # First, simplify all arguments recursively
        simplified_args = [simplify(arg) for arg in expr.args]

        # Check if all arguments are constants
        all_constants = all(isinstance(arg, (int, float)) for arg in simplified_args)

        if all_constants and len(simplified_args) > 0:
            # If all arguments are constants, evaluate the expression
            try:
                # Create a temporary ExprNode with simplified args for evaluation
                temp_expr = ExprNode(op=expr.op, args=simplified_args)
                return evaluate(temp_expr, {})
            except (ValueError, TypeError, ZeroDivisionError):
                # If evaluation fails, return the expression with simplified args
                return ExprNode(op=expr.op, args=simplified_args, wrt=expr.wrt, dim=expr.dim)

        # Apply specific simplification rules
        if expr.op == "+":
            # Remove zeros and combine constants
            non_zero_args = []
            constant_sum = 0
            has_constants = False

            for arg in simplified_args:
                if isinstance(arg, (int, float)):
                    if arg != 0:
                        constant_sum += arg
                        has_constants = True
                else:
                    non_zero_args.append(arg)

            # Add back the constant sum if non-zero or if there are no other terms
            if has_constants and (constant_sum != 0 or len(non_zero_args) == 0):
                non_zero_args.append(constant_sum)

            if len(non_zero_args) == 0:
                return 0
            elif len(non_zero_args) == 1:
                return non_zero_args[0]
            else:
                return ExprNode(op=expr.op, args=non_zero_args, wrt=expr.wrt, dim=expr.dim)

        elif expr.op == "*":
            # Remove ones, handle zeros, and combine constants
            non_one_args = []
            constant_product = 1
            has_constants = False

            for arg in simplified_args:
                if isinstance(arg, (int, float)):
                    if arg == 0:
                        return 0  # Anything times zero is zero
                    elif arg != 1:
                        constant_product *= arg
                        has_constants = True
                else:
                    non_one_args.append(arg)

            # Add back the constant product if not one or if there are no other terms
            if has_constants and (constant_product != 1 or len(non_one_args) == 0):
                non_one_args.append(constant_product)

            if len(non_one_args) == 0:
                return 1
            elif len(non_one_args) == 1:
                return non_one_args[0]
            else:
                return ExprNode(op=expr.op, args=non_one_args, wrt=expr.wrt, dim=expr.dim)

        elif expr.op == "^" or expr.op == "**":
            # Handle special cases like x^0, x^1, 1^y, 0^y
            if len(simplified_args) == 2:
                base, exponent = simplified_args
                if isinstance(exponent, (int, float)) and exponent == 0:
                    return 1  # x^0 = 1
                elif isinstance(exponent, (int, float)) and exponent == 1:
                    return base  # x^1 = x
                elif isinstance(base, (int, float)) and base == 1:
                    return 1  # 1^y = 1
                elif isinstance(base, (int, float)) and base == 0:
                    return 0  # 0^y = 0 (for positive y)

        # If no specific simplifications apply, return with simplified args
        return ExprNode(op=expr.op, args=simplified_args, wrt=expr.wrt, dim=expr.dim)
    else:
        return expr


def to_sympy(expr: Expr, symbol_map: Optional[Dict[str, sp.Symbol]] = None) -> sp.Expr:
    """
    Convert ESM expression to SymPy expression.

    Args:
        expr: ESM expression to convert
        symbol_map: Optional mapping from variable names to SymPy symbols

    Returns:
        SymPy expression

    Raises:
        TypeError: If unsupported expression type or operation is encountered
    """
    if symbol_map is None:
        symbol_map = {}

    if isinstance(expr, (int, float)):
        return sp.sympify(expr)
    elif isinstance(expr, str):
        # Variable name - create symbol if not in map
        if expr not in symbol_map:
            symbol_map[expr] = sp.Symbol(expr)
        return symbol_map[expr]
    elif isinstance(expr, ExprNode):
        # Convert arguments recursively
        sympy_args = [to_sympy(arg, symbol_map) for arg in expr.args]

        # Map operations to SymPy
        if expr.op == "+":
            return sum(sympy_args) if sympy_args else 0
        elif expr.op == "-":
            if len(sympy_args) == 1:
                return -sympy_args[0]
            elif len(sympy_args) == 2:
                return sympy_args[0] - sympy_args[1]
            else:
                raise TypeError(f"Invalid number of arguments for subtraction: {len(sympy_args)}")
        elif expr.op == "*":
            result = 1
            for arg in sympy_args:
                result *= arg
            return result
        elif expr.op == "/":
            if len(sympy_args) != 2:
                raise TypeError(f"Division requires exactly 2 arguments, got {len(sympy_args)}")
            return sympy_args[0] / sympy_args[1]
        elif expr.op in ("^", "**"):
            if len(sympy_args) != 2:
                raise TypeError(f"Power requires exactly 2 arguments, got {len(sympy_args)}")
            return sympy_args[0] ** sympy_args[1]
        elif expr.op == "exp":
            if len(sympy_args) != 1:
                raise TypeError(f"Exponential requires exactly 1 argument, got {len(sympy_args)}")
            return sp.exp(sympy_args[0])
        elif expr.op == "log":
            if len(sympy_args) != 1:
                raise TypeError(f"Logarithm requires exactly 1 argument, got {len(sympy_args)}")
            return sp.log(sympy_args[0])
        elif expr.op == "sin":
            if len(sympy_args) != 1:
                raise TypeError(f"Sine requires exactly 1 argument, got {len(sympy_args)}")
            return sp.sin(sympy_args[0])
        elif expr.op == "cos":
            if len(sympy_args) != 1:
                raise TypeError(f"Cosine requires exactly 1 argument, got {len(sympy_args)}")
            return sp.cos(sympy_args[0])
        elif expr.op == "D" and expr.wrt:
            # Derivative operation
            if len(sympy_args) != 1:
                raise TypeError(f"Derivative requires exactly 1 argument, got {len(sympy_args)}")
            wrt_symbol = to_sympy(expr.wrt, symbol_map)
            return sp.Derivative(sympy_args[0], wrt_symbol)
        elif expr.op == "Pre":
            # Previous value operator - represent as a function
            if len(sympy_args) != 1:
                raise TypeError(f"Pre operator requires exactly 1 argument, got {len(sympy_args)}")
            return sp.Function('Pre')(sympy_args[0])
        elif expr.op == "ifelse":
            # Conditional operator - map to Piecewise
            if len(sympy_args) != 3:
                raise TypeError(f"ifelse requires exactly 3 arguments (condition, true_val, false_val), got {len(sympy_args)}")
            condition, true_val, false_val = sympy_args
            return sp.Piecewise((true_val, condition), (false_val, True))
        elif expr.op == "grad":
            # Gradient operator - represent as derivative for now
            if len(sympy_args) != 1:
                raise TypeError(f"Gradient requires exactly 1 argument, got {len(sympy_args)}")
            # For gradient, we need the dimension info
            if expr.dim:
                dim_symbol = to_sympy(expr.dim, symbol_map)
                return sp.Derivative(sympy_args[0], dim_symbol)
            else:
                # No dimension specified, just return the expression
                return sympy_args[0]
        else:
            raise TypeError(f"Unsupported operation: {expr.op}")
    else:
        raise TypeError(f"Unsupported expression type: {type(expr)}")


def from_sympy(sympy_expr: sp.Expr) -> Expr:
    """
    Convert SymPy expression back to ESM expression.

    Args:
        sympy_expr: SymPy expression to convert

    Returns:
        ESM expression

    Raises:
        TypeError: If unsupported SymPy expression type is encountered
    """
    if isinstance(sympy_expr, (sp.Integer, sp.Rational, sp.Float)):
        return float(sympy_expr)
    elif isinstance(sympy_expr, sp.Symbol):
        return str(sympy_expr)
    elif isinstance(sympy_expr, sp.Add):
        # Addition
        args = [from_sympy(arg) for arg in sympy_expr.args]
        return ExprNode(op="+", args=args)
    elif isinstance(sympy_expr, sp.Mul):
        # Multiplication
        args = [from_sympy(arg) for arg in sympy_expr.args]
        return ExprNode(op="*", args=args)
    elif isinstance(sympy_expr, sp.Pow):
        # Power
        base, exp = sympy_expr.args
        return ExprNode(op="^", args=[from_sympy(base), from_sympy(exp)])
    elif isinstance(sympy_expr, sp.exp):
        # Exponential
        return ExprNode(op="exp", args=[from_sympy(sympy_expr.args[0])])
    elif isinstance(sympy_expr, sp.log):
        # Logarithm
        return ExprNode(op="log", args=[from_sympy(sympy_expr.args[0])])
    elif isinstance(sympy_expr, sp.sin):
        # Sine
        return ExprNode(op="sin", args=[from_sympy(sympy_expr.args[0])])
    elif isinstance(sympy_expr, sp.cos):
        # Cosine
        return ExprNode(op="cos", args=[from_sympy(sympy_expr.args[0])])
    elif isinstance(sympy_expr, sp.Derivative):
        # Derivative
        expr_arg, wrt_arg = sympy_expr.args[0], sympy_expr.args[1]
        return ExprNode(op="D", args=[from_sympy(expr_arg)], wrt=str(wrt_arg))
    elif isinstance(sympy_expr, sp.Piecewise):
        # Piecewise -> ifelse (assuming 2 pieces)
        pieces = sympy_expr.args
        if len(pieces) == 2:
            (true_val, condition), (false_val, _) = pieces
            return ExprNode(op="ifelse", args=[from_sympy(condition), from_sympy(true_val), from_sympy(false_val)])
        else:
            # For more complex piecewise, just return the first expression for now
            return from_sympy(pieces[0][0])
    elif hasattr(sympy_expr, 'func') and str(sympy_expr.func) == 'Pre':
        # Pre function
        return ExprNode(op="Pre", args=[from_sympy(sympy_expr.args[0])])
    elif isinstance(sympy_expr, sp.Function):
        # Generic function - check if it's one we know
        func_name = str(sympy_expr.func)
        if func_name == 'Pre':
            return ExprNode(op="Pre", args=[from_sympy(arg) for arg in sympy_expr.args])
        else:
            # Unknown function - represent as operation with function name
            return ExprNode(op=func_name, args=[from_sympy(arg) for arg in sympy_expr.args])
    elif sympy_expr.is_number:
        # Numeric constant
        return float(sympy_expr)
    else:
        raise TypeError(f"Unsupported SymPy expression type: {type(sympy_expr)}")


def symbolic_jacobian(model: Model) -> sp.Matrix:
    """
    Compute the Jacobian matrix of the ODE system in a model.

    Args:
        model: Model containing state variables and equations

    Returns:
        SymPy Matrix representing the Jacobian

    Raises:
        ValueError: If model has no state variables or equations
    """
    # Get all state variables
    state_vars = []
    for name, var in model.variables.items():
        if var.type == 'state':
            state_vars.append(name)

    if not state_vars:
        raise ValueError("Model has no state variables")

    if not model.equations:
        raise ValueError("Model has no equations")

    # Create symbol map for all variables
    symbol_map = {}
    for var_name in model.variables.keys():
        symbol_map[var_name] = sp.Symbol(var_name)

    # Extract right-hand sides of differential equations
    # Assume equations are of the form d(state_var)/dt = rhs
    rhs_expressions = []

    for equation in model.equations:
        # Convert equation to SymPy
        lhs_sympy = to_sympy(equation.lhs, symbol_map)
        rhs_sympy = to_sympy(equation.rhs, symbol_map)

        # Check if this is a differential equation
        if isinstance(lhs_sympy, sp.Derivative):
            # Extract the function being differentiated
            diff_var = lhs_sympy.args[0]
            if str(diff_var) in state_vars:
                rhs_expressions.append(rhs_sympy)
        else:
            # For non-differential equations, check if lhs is a state variable
            if str(lhs_sympy) in state_vars:
                # Treat as d(lhs)/dt = rhs
                rhs_expressions.append(rhs_sympy)

    if not rhs_expressions:
        # If no differential equations found, use all equation RHS
        for equation in model.equations:
            rhs_sympy = to_sympy(equation.rhs, symbol_map)
            rhs_expressions.append(rhs_sympy)

    # Ensure we have enough expressions
    while len(rhs_expressions) < len(state_vars):
        # Pad with zeros if needed
        rhs_expressions.append(sp.sympify(0))

    # Take only the first n expressions where n = number of state variables
    rhs_expressions = rhs_expressions[:len(state_vars)]

    # Compute Jacobian: J[i,j] = ∂(rhs_i)/∂(state_var_j)
    jacobian_elements = []
    for rhs in rhs_expressions:
        row = []
        for var_name in state_vars:
            var_symbol = symbol_map[var_name]
            partial_derivative = sp.diff(rhs, var_symbol)
            row.append(partial_derivative)
        jacobian_elements.append(row)

    return sp.Matrix(jacobian_elements)