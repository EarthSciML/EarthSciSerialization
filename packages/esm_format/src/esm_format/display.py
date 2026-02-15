"""
Pretty-printing formatters for ESM format expressions, equations, models, and files.

Implements output formats:
- to_unicode(): Unicode mathematical notation with chemical subscripts
- to_latex(): LaTeX mathematical notation

Based on ESM Format Specification Section 6.1
"""

from typing import Union, Dict, Any
try:
    from .types import Expr, ExprNode, Equation, Model, ReactionSystem, EsmFile
except ImportError:
    # For direct imports when testing
    from types import Expr, ExprNode, Equation, Model, ReactionSystem, EsmFile


# Element lookup table for chemical subscript detection (118 elements)
ELEMENTS = {
    # Period 1
    'H', 'He',
    # Period 2
    'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
    # Period 3
    'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar',
    # Period 4
    'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',
    'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr',
    # Period 5
    'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd',
    'In', 'Sn', 'Sb', 'Te', 'I', 'Xe',
    # Period 6
    'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy',
    'Ho', 'Er', 'Tm', 'Yb', 'Lu',
    'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi',
    'Po', 'At', 'Rn',
    # Period 7
    'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf',
    'Es', 'Fm', 'Md', 'No', 'Lr',
    'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn', 'Nh', 'Fl', 'Mc',
    'Lv', 'Ts', 'Og'
}

# Unicode subscripts for digits 0-9
SUBSCRIPT_DIGITS = '₀₁₂₃₄₅₆₇₈₉'


def _to_subscript(n: int) -> str:
    """Convert integer to Unicode subscript digits."""
    return ''.join(SUBSCRIPT_DIGITS[int(d)] for d in str(n))


# Unicode superscripts for digits 0-9 and signs
SUPERSCRIPT_MAP = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻'
}


def _to_superscript(text: str) -> str:
    """Convert text to Unicode superscript."""
    return ''.join(SUPERSCRIPT_MAP.get(c, c) for c in text)


def _has_element_pattern(variable: str) -> bool:
    """Check if a variable has element patterns (for chemical formula detection)."""
    i = 0
    has_element = False

    while i < len(variable):
        # Skip non-alphabetic characters at the start
        while i < len(variable) and not variable[i].isalpha():
            i += 1

        if i >= len(variable):
            break

        # Try 2-character element first
        if i + 1 < len(variable):
            two_char = variable[i:i+2]
            if two_char in ELEMENTS:
                has_element = True
                i += 2
                # Skip digits
                while i < len(variable) and variable[i].isdigit():
                    i += 1
                continue

        # Try 1-character element
        one_char = variable[i]
        if one_char in ELEMENTS:
            has_element = True
            i += 1
            # Skip digits
            while i < len(variable) and variable[i].isdigit():
                i += 1
            continue

        # Not an element, move to next character
        i += 1

    return has_element


def _format_chemical_subscripts(variable: str, format_type: str) -> str:
    """
    Apply element-aware chemical subscript formatting to a variable name.
    Uses greedy 2-char-before-1-char matching for element detection.
    """
    # Check if variable looks like a chemical formula
    has_elements = _has_element_pattern(variable)

    if format_type == 'latex':
        if has_elements:
            # Chemical formula: wrap in \mathrm{} and convert digits to subscripts
            import re
            result = re.sub(r'(\d+)', r'_\1', variable)
            return f'\\mathrm{{{result}}}'
        else:
            # Regular variable: return as-is
            return variable

    if not has_elements:
        # No element pattern found, return as-is
        return variable

    # For unicode: element-aware subscript detection
    result = ''
    i = 0

    while i < len(variable):
        matched = False

        # Try 2-character element first
        if i + 1 < len(variable):
            two_char = variable[i:i+2]
            if two_char in ELEMENTS:
                result += two_char
                i += 2
                # Convert following digits to subscripts
                while i < len(variable) and variable[i].isdigit():
                    result += SUBSCRIPT_DIGITS[int(variable[i])]
                    i += 1
                matched = True

        # Try 1-character element if 2-char didn't match
        if not matched and i < len(variable):
            one_char = variable[i]
            if one_char in ELEMENTS:
                result += one_char
                i += 1
                # Convert following digits to subscripts
                while i < len(variable) and variable[i].isdigit():
                    result += SUBSCRIPT_DIGITS[int(variable[i])]
                    i += 1
                matched = True

        # If not an element, copy character as-is
        if not matched:
            result += variable[i]
            i += 1

    return result


def _format_number(num: Union[int, float], format_type: str) -> str:
    """Format a number in scientific notation with appropriate formatting."""
    if isinstance(num, int) and abs(num) < 1e6:
        return str(num)

    if isinstance(num, float) and abs(num) < 1e6 and num.is_integer():
        return str(int(num))

    # Use scientific notation for large numbers or floats
    str_repr = f"{num:.12e}"
    if 'e' not in str_repr:
        return str_repr

    mantissa, exponent = str_repr.split('e')
    # Clean up mantissa by removing trailing zeros
    mantissa = mantissa.rstrip('0').rstrip('.')
    exp = int(exponent)

    if format_type == 'unicode':
        return f"{mantissa}×10{_to_superscript(str(exp))}"
    elif format_type == 'latex':
        return f"{mantissa} \\times 10^{{{exp}}}"
    else:
        return str_repr  # Plain scientific notation


def _get_operator_precedence(op: str) -> int:
    """Get operator precedence for proper parenthesization."""
    precedence_map = {
        'or': 1,
        'and': 2,
        '==': 3, '!=': 3, '<': 3, '>': 3, '<=': 3, '>=': 3,
        '+': 4, '-': 4,
        '*': 5, '/': 5,
        'not': 6,  # Unary
        '^': 7,
    }
    return precedence_map.get(op, 8)  # Functions get highest precedence


def _needs_parentheses(parent: ExprNode, child: Expr, is_right_operand: bool = False) -> bool:
    """Check if parentheses are needed around a subexpression."""
    if isinstance(child, (int, float, str)):
        return False

    if not isinstance(child, ExprNode):
        return False

    parent_prec = _get_operator_precedence(parent.op)
    child_prec = _get_operator_precedence(child.op)

    if child_prec < parent_prec:
        return True
    if child_prec > parent_prec:
        return False

    # Same precedence: need parens if child is right operand and operator is not associative
    if is_right_operand and parent.op in ['-', '/', '^']:
        return True

    # Special cases for function arguments - no parens needed for simple expressions
    if parent.op in ['sin', 'cos', 'tan', 'exp', 'log', 'sqrt', 'abs']:
        # Only parenthesize for very low precedence operators
        return child_prec <= 2

    return False


def to_unicode(target: Union[Expr, Equation, Model, ReactionSystem, EsmFile]) -> str:
    """
    Format target as Unicode mathematical notation with chemical subscripts.

    Args:
        target: Expression, equation, model, reaction system, or ESM file to format

    Returns:
        Unicode string representation
    """
    if isinstance(target, (int, float)):
        return _format_number(target, 'unicode')

    if isinstance(target, str):
        return _format_chemical_subscripts(target, 'unicode')

    if isinstance(target, ExprNode):
        return _format_expression_node(target, 'unicode')

    if isinstance(target, Equation):
        return f"{to_unicode(target.lhs)} = {to_unicode(target.rhs)}"

    if isinstance(target, EsmFile):
        return _format_esm_file_summary(target, 'unicode')

    if isinstance(target, Model):
        return _format_model_summary(target, 'unicode')

    if isinstance(target, ReactionSystem):
        return _format_reaction_system_summary(target, 'unicode')

    raise ValueError(f"Unsupported type for Unicode formatting: {type(target)}")


def to_latex(target: Union[Expr, Equation, Model, ReactionSystem, EsmFile]) -> str:
    """
    Format target as LaTeX mathematical notation.

    Args:
        target: Expression, equation, model, reaction system, or ESM file to format

    Returns:
        LaTeX string representation
    """
    if isinstance(target, (int, float)):
        return _format_number(target, 'latex')

    if isinstance(target, str):
        return _format_chemical_subscripts(target, 'latex')

    if isinstance(target, ExprNode):
        return _format_expression_node(target, 'latex')

    if isinstance(target, Equation):
        return f"{to_latex(target.lhs)} = {to_latex(target.rhs)}"

    if isinstance(target, EsmFile):
        # ESM files not typically formatted as LaTeX, return plain text
        return _format_esm_file_summary(target, 'ascii')

    if isinstance(target, Model):
        # Models not typically formatted as LaTeX, return plain text
        return _format_model_summary(target, 'ascii')

    if isinstance(target, ReactionSystem):
        # Reaction systems not typically formatted as LaTeX, return plain text
        return _format_reaction_system_summary(target, 'ascii')

    raise ValueError(f"Unsupported type for LaTeX formatting: {type(target)}")


def _format_expression_node(node: ExprNode, format_type: str) -> str:
    """Format an ExpressionNode (operator with arguments)."""
    op, args = node.op, node.args
    wrt = getattr(node, 'wrt', None)

    # Helper to format arguments with proper parenthesization
    def format_arg(arg: Expr, is_right_operand: bool = False) -> str:
        if format_type == 'unicode':
            result = to_unicode(arg)
        elif format_type == 'latex':
            result = to_latex(arg)
        else:
            raise ValueError(f"Unknown format type: {format_type}")

        if _needs_parentheses(node, arg, is_right_operand):
            if format_type == 'latex':
                return f'\\left({result}\\right)'
            else:
                return f'({result})'
        return result

    # Binary operators
    if len(args) == 2:
        left, right = args

        if op == '+':
            return f"{format_arg(left)} + {format_arg(right, True)}"

        elif op == '-':
            if format_type == 'unicode':
                return f"{format_arg(left)} − {format_arg(right, True)}"
            return f"{format_arg(left)} - {format_arg(right, True)}"

        elif op == '*':
            if format_type == 'unicode':
                return f"{format_arg(left)}·{format_arg(right, True)}"
            elif format_type == 'latex':
                return f"{format_arg(left)} \\cdot {format_arg(right, True)}"

        elif op == '/':
            if format_type == 'latex':
                return f"\\frac{{{to_latex(left)}}}{{{to_latex(right)}}}"
            elif format_type == 'unicode':
                return f"{format_arg(left)}/{format_arg(right, True)}"

        elif op == '^':
            if format_type == 'latex':
                return f"{format_arg(left)}^{{{to_latex(right)}}}"
            # For unicode, try to use superscript digits
            if format_type == 'unicode' and isinstance(right, int):
                return f"{format_arg(left)}{_to_superscript(str(right))}"
            return f"{format_arg(left)}^{format_arg(right, True)}"

        elif op in ['>', '<']:
            return f"{format_arg(left)} {op} {format_arg(right, True)}"

        elif op == '>=':
            if format_type == 'unicode':
                return f"{format_arg(left)} ≥ {format_arg(right, True)}"
            return f"{format_arg(left)} >= {format_arg(right, True)}"

        elif op == '<=':
            if format_type == 'unicode':
                return f"{format_arg(left)} ≤ {format_arg(right, True)}"
            return f"{format_arg(left)} <= {format_arg(right, True)}"

        elif op == '==':
            if format_type == 'unicode':
                return f"{format_arg(left)} = {format_arg(right, True)}"
            return f"{format_arg(left)} == {format_arg(right, True)}"

        elif op == '!=':
            if format_type == 'unicode':
                return f"{format_arg(left)} ≠ {format_arg(right, True)}"
            return f"{format_arg(left)} != {format_arg(right, True)}"

        elif op == 'and':
            if format_type == 'unicode':
                return f"{format_arg(left)} ∧ {format_arg(right, True)}"
            return f"{format_arg(left)} and {format_arg(right, True)}"

        elif op == 'or':
            if format_type == 'unicode':
                return f"{format_arg(left)} ∨ {format_arg(right, True)}"
            return f"{format_arg(left)} or {format_arg(right, True)}"

        elif op in ['min', 'max']:
            if format_type == 'latex':
                return f"\\{op}({to_latex(left)}, {to_latex(right)})"
            return f"{op}({format_arg(left)}, {format_arg(right)})"

    # Unary operators
    elif len(args) == 1:
        arg = args[0]

        if op == '-':
            # Unary minus
            if format_type == 'unicode':
                return f"−{format_arg(arg)}"
            return f"-{format_arg(arg)}"

        elif op == 'not':
            if format_type == 'unicode':
                return f"¬{format_arg(arg)}"
            return f"not {format_arg(arg)}"

        elif op in ['exp', 'sin', 'cos', 'tan']:
            if format_type == 'latex':
                return f"\\{op}\\left({to_latex(arg)}\\right)"
            return f"{op}({format_arg(arg)})"

        elif op == 'log':
            if format_type == 'unicode':
                return f"ln({format_arg(arg)})"
            elif format_type == 'latex':
                return f"\\log\\left({to_latex(arg)}\\right)"

        elif op == 'sqrt':
            if format_type == 'unicode':
                return f"√{format_arg(arg)}"
            elif format_type == 'latex':
                return f"\\sqrt{{{to_latex(arg)}}}"

        elif op == 'abs':
            if format_type == 'unicode':
                return f"|{format_arg(arg)}|"
            elif format_type == 'latex':
                return f"|{to_latex(arg)}|"

        elif op == 'D':
            # Derivative operator
            wrt_var = wrt or 't'
            if format_type == 'unicode':
                variable = to_unicode(arg)
                return f"∂{variable}/∂{wrt_var}"
            elif format_type == 'latex':
                return f"\\frac{{\\partial {to_latex(arg)}}}{{\\partial {wrt_var}}}"

    # Fallback: function call notation
    if format_type == 'unicode':
        arg_list = ', '.join(to_unicode(arg) for arg in args)
    elif format_type == 'latex':
        arg_list = ', '.join(to_latex(arg) for arg in args)
        return f"\\text{{{op}}}\\left({arg_list}\\right)"

    return f"{op}({arg_list})"


def _format_model_summary(model: Model, format_type: str) -> str:
    """Format model summary (implementation per spec Section 6.3)."""
    name = getattr(model, 'name', 'unnamed')
    var_count = len(model.variables) if model.variables else 0
    eq_count = len(model.equations) if model.equations else 0
    return f"Model: {name} ({var_count} variables, {eq_count} equations)"


def _format_reaction_system_summary(reaction_system: ReactionSystem, format_type: str) -> str:
    """Format reaction system summary showing reactions in chemical notation."""
    name = getattr(reaction_system, 'name', 'unnamed')
    species_count = len(reaction_system.species) if reaction_system.species else 0
    reaction_count = len(reaction_system.reactions) if reaction_system.reactions else 0
    return f"ReactionSystem: {name} ({species_count} species, {reaction_count} reactions)"


def _format_esm_file_summary(esm_file: EsmFile, format_type: str) -> str:
    """Format ESM file summary (implementation per spec Section 6.3)."""
    models_count = len(esm_file.models) if esm_file.models else 0
    reaction_systems_count = len(esm_file.reaction_systems) if esm_file.reaction_systems else 0
    data_loaders_count = len(esm_file.data_loaders) if esm_file.data_loaders else 0
    title = getattr(esm_file.metadata, 'title', 'Untitled')

    return f"ESM v{esm_file.version}: {title} ({models_count} models, {reaction_systems_count} reaction systems, {data_loaders_count} data loaders)"


# Add _repr_latex_ methods for Jupyter notebook rich display

def _add_repr_methods():
    """Add _repr_latex_ methods to classes for Jupyter rich display."""

    def esm_file_repr_latex(self) -> str:
        return to_latex(self)

    def model_repr_latex(self) -> str:
        return to_latex(self)

    def reaction_system_repr_latex(self) -> str:
        return to_latex(self)

    def equation_repr_latex(self) -> str:
        return to_latex(self)

    # Add methods to classes
    EsmFile._repr_latex_ = esm_file_repr_latex
    Model._repr_latex_ = model_repr_latex
    ReactionSystem._repr_latex_ = reaction_system_repr_latex
    Equation._repr_latex_ = equation_repr_latex


# Initialize the _repr_latex_ methods when the module is imported
_add_repr_methods()