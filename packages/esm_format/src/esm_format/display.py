"""
Pretty-printing formatters for ESM format expressions, equations, models, and files.

Implements output formats:
- to_unicode(): Unicode mathematical notation with chemical subscripts
- to_latex(): LaTeX mathematical notation

Based on ESM Format Specification Section 6.1
"""

from typing import Union, Dict, Any
try:
    from .esm_types import Expr, ExprNode, Equation, Model, ReactionSystem, EsmFile
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


# ========================================
# Jupyter Integration and Interactive Display
# ========================================

def explore(esm_file: EsmFile) -> 'ESMExplorer':
    """
    Create an interactive widget for exploring ESM files in Jupyter notebooks.

    Args:
        esm_file: The ESM file to explore

    Returns:
        ESMExplorer widget for interactive exploration
    """
    return ESMExplorer(esm_file)


class ESMExplorer:
    """Interactive explorer widget for ESM files in Jupyter notebooks."""

    def __init__(self, esm_file: EsmFile):
        """Initialize the ESM explorer."""
        self.esm_file = esm_file

    def _repr_html_(self) -> str:
        """Rich HTML representation for Jupyter notebooks."""
        html_parts = []

        # Header
        title = getattr(self.esm_file.metadata, 'title', 'Untitled ESM File')
        html_parts.append(f"""
        <div style="border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin: 10px 0; background-color: #f9f9f9;">
            <h3 style="margin-top: 0; color: #333;">📊 {title}</h3>
            <p><strong>Version:</strong> {self.esm_file.version}</p>
        """)

        # Summary statistics
        models_count = len(self.esm_file.models) if self.esm_file.models else 0
        rs_count = len(self.esm_file.reaction_systems) if self.esm_file.reaction_systems else 0
        data_loaders_count = len(self.esm_file.data_loaders) if self.esm_file.data_loaders else 0

        html_parts.append(f"""
            <div style="display: flex; gap: 20px; margin: 10px 0;">
                <div><span style="font-weight: bold; color: #2E86AB;">Models:</span> {models_count}</div>
                <div><span style="font-weight: bold; color: #A23B72;">Reaction Systems:</span> {rs_count}</div>
                <div><span style="font-weight: bold; color: #F18F01;">Data Loaders:</span> {data_loaders_count}</div>
            </div>
        """)

        # Models section
        if self.esm_file.models:
            html_parts.append('<h4 style="color: #2E86AB; margin-top: 20px;">🔬 Models</h4>')
            for model in self.esm_file.models:
                var_count = len(model.variables) if model.variables else 0
                eq_count = len(model.equations) if model.equations else 0

                html_parts.append(f"""
                <div style="margin: 10px 0; padding: 10px; border-left: 4px solid #2E86AB; background-color: #f0f8ff;">
                    <strong>{model.name}</strong><br>
                    <small>{var_count} variables, {eq_count} equations</small>
                    <div style="margin-top: 5px;">
                        <details style="cursor: pointer;">
                            <summary style="font-size: 0.9em; color: #666;">Show variables</summary>
                            <div style="margin-top: 5px; font-size: 0.8em;">
                """)

                if model.variables:
                    for var_name, var_info in model.variables.items():
                        var_type = getattr(var_info, 'type', 'unknown')
                        units = getattr(var_info, 'units', None)
                        units_str = f" [{units}]" if units else ""
                        html_parts.append(f"<div>• {var_name} ({var_type}){units_str}</div>")

                html_parts.append("""
                            </div>
                        </details>
                    </div>
                </div>
                """)

        # Reaction Systems section
        if self.esm_file.reaction_systems:
            html_parts.append('<h4 style="color: #A23B72; margin-top: 20px;">⚗️ Reaction Systems</h4>')
            for rs in self.esm_file.reaction_systems:
                species_count = len(rs.species) if rs.species else 0
                reaction_count = len(rs.reactions) if rs.reactions else 0

                html_parts.append(f"""
                <div style="margin: 10px 0; padding: 10px; border-left: 4px solid #A23B72; background-color: #fdf0f5;">
                    <strong>{rs.name}</strong><br>
                    <small>{species_count} species, {reaction_count} reactions</small>
                    <div style="margin-top: 5px;">
                        <details style="cursor: pointer;">
                            <summary style="font-size: 0.9em; color: #666;">Show reactions</summary>
                            <div style="margin-top: 5px; font-size: 0.8em;">
                """)

                if rs.reactions:
                    for reaction in rs.reactions:
                        # Format reaction equation
                        reactants = [f"{coef}×{species}" if coef != 1 else species
                                   for species, coef in reaction.reactants.items()] if reaction.reactants else []
                        products = [f"{coef}×{species}" if coef != 1 else species
                                  for species, coef in reaction.products.items()] if reaction.products else []

                        reactant_str = " + ".join(reactants) if reactants else "∅"
                        product_str = " + ".join(products) if products else "∅"

                        html_parts.append(f"<div>• {reaction.name}: {reactant_str} → {product_str}</div>")

                html_parts.append("""
                            </div>
                        </details>
                    </div>
                </div>
                """)

        # Data Loaders section
        if self.esm_file.data_loaders:
            html_parts.append('<h4 style="color: #F18F01; margin-top: 20px;">📁 Data Loaders</h4>')
            for loader in self.esm_file.data_loaders:
                loader_type = getattr(loader, 'type', 'unknown')
                html_parts.append(f"""
                <div style="margin: 10px 0; padding: 10px; border-left: 4px solid #F18F01; background-color: #fefbf0;">
                    <strong>{loader.name}</strong> ({loader_type})<br>
                </div>
                """)

        # Coupling Graph section
        html_parts.append('<h4 style="color: #666; margin-top: 20px;">🔗 Coupling Analysis</h4>')
        try:
            from .graph import component_graph
            graph = component_graph(self.esm_file)
            coupling_count = len(graph.edges)
            html_parts.append(f"""
            <div style="margin: 10px 0; padding: 10px; border-left: 4px solid #666; background-color: #f5f5f5;">
                <strong>Component Graph:</strong> {len(graph.nodes)} nodes, {coupling_count} couplings<br>
                <details style="cursor: pointer; margin-top: 5px;">
                    <summary style="font-size: 0.9em; color: #666;">Show graph formats</summary>
                    <div style="margin-top: 10px;">
                        <button onclick="navigator.clipboard.writeText(this.nextElementSibling.textContent)"
                                style="background: #007cba; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; margin: 2px;">
                            Copy DOT
                        </button>
                        <pre style="background: #f8f8f8; padding: 10px; border-radius: 3px; overflow-x: auto; font-size: 0.8em;">{graph.to_dot()}</pre>

                        <button onclick="navigator.clipboard.writeText(this.nextElementSibling.textContent)"
                                style="background: #ff6b6b; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; margin: 2px;">
                            Copy Mermaid
                        </button>
                        <pre style="background: #f8f8f8; padding: 10px; border-radius: 3px; overflow-x: auto; font-size: 0.8em;">{graph.to_mermaid()}</pre>
                    </div>
                </details>
            </div>
            """)
        except Exception as e:
            html_parts.append(f"""
            <div style="margin: 10px 0; padding: 10px; border-left: 4px solid #ff6b6b; background-color: #ffeeee;">
                <small>Could not generate coupling graph: {e}</small>
            </div>
            """)

        # Close main div
        html_parts.append('</div>')

        return ''.join(html_parts)

    def show_models(self):
        """Display detailed information about models."""
        if not self.esm_file.models:
            print("No models in this ESM file.")
            return

        for model in self.esm_file.models:
            print(f"\n📊 Model: {model.name}")
            print(f"   Variables: {len(model.variables) if model.variables else 0}")
            print(f"   Equations: {len(model.equations) if model.equations else 0}")

            if model.variables:
                print("   Variable details:")
                for var_name, var_info in model.variables.items():
                    var_type = getattr(var_info, 'type', 'unknown')
                    units = getattr(var_info, 'units', None)
                    units_str = f" [{units}]" if units else ""
                    print(f"     • {var_name} ({var_type}){units_str}")

    def show_reactions(self):
        """Display detailed information about reaction systems."""
        if not self.esm_file.reaction_systems:
            print("No reaction systems in this ESM file.")
            return

        for rs in self.esm_file.reaction_systems:
            print(f"\n⚗️ Reaction System: {rs.name}")
            print(f"   Species: {len(rs.species) if rs.species else 0}")
            print(f"   Reactions: {len(rs.reactions) if rs.reactions else 0}")

            if rs.reactions:
                print("   Reaction details:")
                for reaction in rs.reactions:
                    # Format reaction equation
                    reactants = [f"{coef}*{species}" if coef != 1 else species
                               for species, coef in reaction.reactants.items()] if reaction.reactants else []
                    products = [f"{coef}*{species}" if coef != 1 else species
                              for species, coef in reaction.products.items()] if reaction.products else []

                    reactant_str = " + ".join(reactants) if reactants else "∅"
                    product_str = " + ".join(products) if products else "∅"

                    print(f"     • {reaction.name}: {reactant_str} → {product_str}")

    def show_graph(self, format_type: str = "mermaid"):
        """Display the component graph in the specified format."""
        try:
            from .graph import component_graph
            graph = component_graph(self.esm_file)

            if format_type.lower() == "dot":
                print("DOT format:")
                print(graph.to_dot())
            elif format_type.lower() == "mermaid":
                print("Mermaid format:")
                print(graph.to_mermaid())
            elif format_type.lower() == "json":
                print("JSON format:")
                print(graph.to_json())
            else:
                print(f"Unknown format: {format_type}. Supported: dot, mermaid, json")
        except Exception as e:
            print(f"Error generating graph: {e}")


def _add_enhanced_repr_methods():
    """Add enhanced _repr_html_ methods to classes for rich Jupyter display."""

    def esm_file_repr_html(self) -> str:
        """Enhanced HTML representation for ESM files."""
        explorer = ESMExplorer(self)
        return explorer._repr_html_()

    def model_repr_html(self) -> str:
        """Enhanced HTML representation for models."""
        var_count = len(self.variables) if self.variables else 0
        eq_count = len(self.equations) if self.equations else 0

        html = f"""
        <div style="border: 1px solid #2E86AB; border-radius: 5px; padding: 10px; margin: 5px 0; background-color: #f0f8ff;">
            <h4 style="margin-top: 0; color: #2E86AB;">🔬 Model: {self.name}</h4>
            <p><strong>Variables:</strong> {var_count} | <strong>Equations:</strong> {eq_count}</p>
        """

        if self.variables:
            html += '<details><summary style="cursor: pointer; color: #666;">Show variables</summary><ul style="margin: 5px 0;">'
            for var_name, var_info in self.variables.items():
                var_type = getattr(var_info, 'type', 'unknown')
                units = getattr(var_info, 'units', None)
                units_str = f" [{units}]" if units else ""
                html += f"<li>{var_name} ({var_type}){units_str}</li>"
            html += '</ul></details>'

        html += '</div>'
        return html

    def reaction_system_repr_html(self) -> str:
        """Enhanced HTML representation for reaction systems."""
        species_count = len(self.species) if self.species else 0
        reaction_count = len(self.reactions) if self.reactions else 0

        html = f"""
        <div style="border: 1px solid #A23B72; border-radius: 5px; padding: 10px; margin: 5px 0; background-color: #fdf0f5;">
            <h4 style="margin-top: 0; color: #A23B72;">⚗️ Reaction System: {self.name}</h4>
            <p><strong>Species:</strong> {species_count} | <strong>Reactions:</strong> {reaction_count}</p>
        """

        if self.reactions:
            html += '<details><summary style="cursor: pointer; color: #666;">Show reactions</summary><ul style="margin: 5px 0;">'
            for reaction in self.reactions:
                # Format reaction equation
                reactants = [f"{coef}×{species}" if coef != 1 else species
                           for species, coef in reaction.reactants.items()] if reaction.reactants else []
                products = [f"{coef}×{species}" if coef != 1 else species
                          for species, coef in reaction.products.items()] if reaction.products else []

                reactant_str = " + ".join(reactants) if reactants else "∅"
                product_str = " + ".join(products) if products else "∅"

                html += f"<li><strong>{reaction.name}:</strong> {reactant_str} → {product_str}</li>"
            html += '</ul></details>'

        html += '</div>'
        return html

    def equation_repr_html(self) -> str:
        """Enhanced HTML representation for equations."""
        try:
            lhs_str = to_unicode(self.lhs)
            rhs_str = to_unicode(self.rhs)
            return f"""
            <div style="border: 1px solid #666; border-radius: 3px; padding: 8px; margin: 3px 0; background-color: #fafafa; font-family: 'Times New Roman', serif;">
                <span style="font-size: 1.1em;">{lhs_str} = {rhs_str}</span>
            </div>
            """
        except:
            return f"<code>{self.lhs} = {self.rhs}</code>"

    # Add methods to classes
    EsmFile._repr_html_ = esm_file_repr_html
    Model._repr_html_ = model_repr_html
    ReactionSystem._repr_html_ = reaction_system_repr_html
    Equation._repr_html_ = equation_repr_html


# Initialize enhanced HTML representation methods
_add_enhanced_repr_methods()