"""
Expression manipulation and analysis functions.
"""

from typing import Dict, Set, Union
from .types import Expr, ExprNode, Model, ReactionSystem


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