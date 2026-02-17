"""
Placeholder expansion algorithm for _var syntax in ESM format expressions.

This module provides functionality to expand _var placeholders in expressions
with actual variable names, including recursive expansion, circular reference
detection, and expansion context management.
"""

from typing import Union, Dict, Any, Set, List, Optional
from .esm_types import Expr, ExprNode


class CircularReferenceError(Exception):
    """Exception raised when circular references are detected in placeholder expansion."""
    pass


class PlaceholderExpansionError(Exception):
    """Exception raised when placeholder expansion fails."""
    pass


class ExpansionContext:
    """
    Context manager for placeholder expansion operations.

    Tracks expansion state, detects circular references, and manages
    the expansion process across nested expressions.
    """

    def __init__(self):
        self._expansion_stack: List[str] = []
        self._expanded_placeholders: Set[str] = set()

    def enter_expansion(self, variable_name: str) -> None:
        """
        Enter expansion of a specific variable.

        Args:
            variable_name: The variable being expanded

        Raises:
            CircularReferenceError: If circular reference detected
        """
        if variable_name in self._expansion_stack:
            cycle_path = " -> ".join(self._expansion_stack + [variable_name])
            raise CircularReferenceError(
                f"Circular reference detected in placeholder expansion: {cycle_path}"
            )

        self._expansion_stack.append(variable_name)

    def exit_expansion(self) -> None:
        """Exit the current expansion level."""
        if self._expansion_stack:
            variable_name = self._expansion_stack.pop()
            self._expanded_placeholders.add(variable_name)

    def is_expanded(self, variable_name: str) -> bool:
        """Check if a variable has already been expanded."""
        return variable_name in self._expanded_placeholders

    def get_expansion_depth(self) -> int:
        """Get current expansion depth."""
        return len(self._expansion_stack)

    def get_current_path(self) -> List[str]:
        """Get current expansion path."""
        return self._expansion_stack.copy()


def expand_placeholder(
    expression: Expr,
    target_variable: str,
    context: Optional[ExpansionContext] = None,
    max_depth: int = 10
) -> Expr:
    """
    Expand _var placeholders in an expression with a target variable name.

    Args:
        expression: The expression containing _var placeholders
        target_variable: The variable name to substitute for _var
        context: Optional expansion context for recursive calls
        max_depth: Maximum recursion depth to prevent infinite expansion

    Returns:
        Expression with _var placeholders replaced by target_variable

    Raises:
        CircularReferenceError: If circular references detected
        PlaceholderExpansionError: If expansion fails
    """
    if context is None:
        context = ExpansionContext()

    # Check recursion depth before entering expansion
    if context.get_expansion_depth() >= max_depth:
        raise PlaceholderExpansionError(
            f"Maximum expansion depth ({max_depth}) exceeded. "
            f"Current path: {' -> '.join(context.get_current_path())}"
        )

    # Track this expansion
    context.enter_expansion(target_variable)

    try:
        result = _expand_expression(expression, target_variable, context, max_depth, 0)
        return result
    finally:
        context.exit_expansion()


def _expand_expression(
    expression: Expr,
    target_variable: str,
    context: ExpansionContext,
    max_depth: int,
    current_depth: int = 0
) -> Expr:
    """
    Internal recursive function to expand expressions.

    Args:
        expression: Expression to expand
        target_variable: Target variable name
        context: Expansion context
        max_depth: Maximum recursion depth
        current_depth: Current recursion depth

    Returns:
        Expanded expression
    """
    # Check structural recursion depth
    if current_depth > max_depth:
        raise PlaceholderExpansionError(
            f"Maximum structural depth ({max_depth}) exceeded during expansion"
        )

    # Handle string expressions (base case)
    if isinstance(expression, str):
        if expression == "_var":
            return target_variable
        return expression

    # Handle numeric expressions (base case)
    if isinstance(expression, (int, float)):
        return expression

    # Handle expression nodes
    if isinstance(expression, ExprNode):
        # Recursively expand all arguments
        expanded_args = []
        for arg in expression.args:
            expanded_arg = _expand_expression(arg, target_variable, context, max_depth, current_depth + 1)
            expanded_args.append(expanded_arg)

        # Create new expression node with expanded arguments
        expanded_node = ExprNode(
            op=expression.op,
            args=expanded_args
        )

        # Copy additional attributes if they exist
        if hasattr(expression, 'wrt'):
            expanded_node.wrt = expression.wrt
        if hasattr(expression, 'dim'):
            expanded_node.dim = expression.dim
        if hasattr(expression, 'boundary'):
            expanded_node.boundary = expression.boundary

        return expanded_node

    # Handle other types (lists, dictionaries, etc.)
    if isinstance(expression, list):
        return [_expand_expression(item, target_variable, context, max_depth, current_depth + 1)
                for item in expression]

    if isinstance(expression, dict):
        # Check if this is a raw dict that should be converted to ExprNode
        if "op" in expression and "args" in expression:
            from .parse import _parse_expression
            # Parse it first, then expand
            parsed_expr = _parse_expression(expression)
            return _expand_expression(parsed_expr, target_variable, context, max_depth, current_depth + 1)
        else:
            # Regular dictionary
            return {key: _expand_expression(value, target_variable, context, max_depth, current_depth + 1)
                    for key, value in expression.items()}

    # Return unchanged for unknown types
    return expression


def expand_multiple_placeholders(
    expression: Expr,
    placeholder_map: Dict[str, str],
    context: Optional[ExpansionContext] = None,
    max_depth: int = 10
) -> Expr:
    """
    Expand multiple placeholder patterns in an expression.

    Args:
        expression: Expression containing placeholders
        placeholder_map: Mapping from placeholder patterns to target variables
                        e.g., {"_var": "temperature", "_var2": "pressure"}
        context: Optional expansion context
        max_depth: Maximum recursion depth

    Returns:
        Expression with all placeholders expanded

    Raises:
        CircularReferenceError: If circular references detected
        PlaceholderExpansionError: If expansion fails
    """
    if context is None:
        context = ExpansionContext()

    result = expression

    # Expand each placeholder pattern
    for placeholder, target_var in placeholder_map.items():
        if context.get_expansion_depth() >= max_depth:
            raise PlaceholderExpansionError(
                f"Maximum expansion depth ({max_depth}) exceeded during multiple expansion"
            )

        result = _expand_multiple_recursive(result, placeholder, target_var, context, max_depth)

    return result


def _expand_multiple_recursive(
    expression: Expr,
    placeholder: str,
    target_variable: str,
    context: ExpansionContext,
    max_depth: int
) -> Expr:
    """
    Internal function for expanding multiple placeholders recursively.
    """
    # Handle string expressions
    if isinstance(expression, str):
        if expression == placeholder:
            return target_variable
        return expression

    # Handle numeric expressions
    if isinstance(expression, (int, float)):
        return expression

    # Handle expression nodes
    if isinstance(expression, ExprNode):
        expanded_args = []
        for arg in expression.args:
            expanded_arg = _expand_multiple_recursive(
                arg, placeholder, target_variable, context, max_depth
            )
            expanded_args.append(expanded_arg)

        expanded_node = ExprNode(
            op=expression.op,
            args=expanded_args
        )

        # Copy attributes
        if hasattr(expression, 'wrt'):
            expanded_node.wrt = expression.wrt
        if hasattr(expression, 'dim'):
            expanded_node.dim = expression.dim
        if hasattr(expression, 'boundary'):
            expanded_node.boundary = expression.boundary

        return expanded_node

    # Handle collections
    if isinstance(expression, list):
        return [_expand_multiple_recursive(item, placeholder, target_variable, context, max_depth)
                for item in expression]

    if isinstance(expression, dict):
        # Check if this is a raw dict that should be converted to ExprNode
        if "op" in expression and "args" in expression:
            from .parse import _parse_expression
            # Parse it first, then expand
            parsed_expr = _parse_expression(expression)
            return _expand_multiple_recursive(parsed_expr, placeholder, target_variable, context, max_depth)
        else:
            # Regular dictionary
            return {key: _expand_multiple_recursive(value, placeholder, target_variable, context, max_depth)
                    for key, value in expression.items()}

    return expression


def validate_placeholder_expansion(
    original_expression: Expr,
    expanded_expression: Expr,
    target_variable: str
) -> bool:
    """
    Validate that placeholder expansion was performed correctly.

    Args:
        original_expression: Original expression with placeholders
        expanded_expression: Expanded expression
        target_variable: Target variable used in expansion

    Returns:
        True if expansion is valid, False otherwise
    """
    # Check that no _var placeholders remain in expanded expression
    if _contains_placeholder(expanded_expression, "_var"):
        return False

    # Check that target variable appears in expanded expression
    # (only if original contained _var)
    if _contains_placeholder(original_expression, "_var"):
        if not _contains_variable(expanded_expression, target_variable):
            return False

    return True


def _contains_placeholder(expression: Expr, placeholder: str) -> bool:
    """Check if expression contains a specific placeholder."""
    if isinstance(expression, str):
        return expression == placeholder

    if isinstance(expression, ExprNode):
        return any(_contains_placeholder(arg, placeholder) for arg in expression.args)

    if isinstance(expression, list):
        return any(_contains_placeholder(item, placeholder) for item in expression)

    if isinstance(expression, dict):
        return any(_contains_placeholder(value, placeholder) for value in expression.values())

    return False


def _contains_variable(expression: Expr, variable: str) -> bool:
    """Check if expression contains a specific variable."""
    if isinstance(expression, str):
        return expression == variable

    if isinstance(expression, ExprNode):
        return any(_contains_variable(arg, variable) for arg in expression.args)

    if isinstance(expression, list):
        return any(_contains_variable(item, variable) for item in expression)

    if isinstance(expression, dict):
        return any(_contains_variable(value, variable) for value in expression.values())

    return False


def get_placeholder_variables(expression: Expr) -> Set[str]:
    """
    Extract all placeholder variables from an expression.

    Args:
        expression: Expression to analyze

    Returns:
        Set of placeholder variable names found in the expression
    """
    placeholders = set()

    if isinstance(expression, str):
        if expression.startswith("_"):
            placeholders.add(expression)

    elif isinstance(expression, ExprNode):
        for arg in expression.args:
            placeholders.update(get_placeholder_variables(arg))

    elif isinstance(expression, list):
        for item in expression:
            placeholders.update(get_placeholder_variables(item))

    elif isinstance(expression, dict):
        for value in expression.values():
            placeholders.update(get_placeholder_variables(value))

    return placeholders


def create_expansion_template(
    expression: Expr,
    placeholder_variables: Optional[Set[str]] = None
) -> Dict[str, Any]:
    """
    Create an expansion template from an expression with placeholders.

    Args:
        expression: Expression containing placeholders
        placeholder_variables: Optional set of expected placeholders

    Returns:
        Template dictionary with metadata about the expansion
    """
    if placeholder_variables is None:
        placeholder_variables = get_placeholder_variables(expression)

    return {
        "template_expression": expression,
        "placeholder_variables": list(placeholder_variables),
        "expansion_metadata": {
            "requires_expansion": len(placeholder_variables) > 0,
            "placeholder_count": len(placeholder_variables),
            "complexity_score": _calculate_expression_complexity(expression)
        }
    }


def _calculate_expression_complexity(expression: Expr) -> int:
    """
    Calculate a complexity score for an expression.

    Higher scores indicate more complex expressions that may be
    more expensive to expand.
    """
    if isinstance(expression, (str, int, float)):
        return 1

    if isinstance(expression, ExprNode):
        return 1 + sum(_calculate_expression_complexity(arg) for arg in expression.args)

    if isinstance(expression, list):
        return sum(_calculate_expression_complexity(item) for item in expression)

    if isinstance(expression, dict):
        return sum(_calculate_expression_complexity(value) for value in expression.values())

    return 1