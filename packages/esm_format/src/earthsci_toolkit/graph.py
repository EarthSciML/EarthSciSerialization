"""
Graph representations for ESM Format structures.

Implements component_graph() and expression_graph() functions per ESM Format
Specification Section 4.8, with export capabilities to DOT, Mermaid, and JSON formats.
"""

from typing import Dict, List, Set, Union, Any, Optional
from dataclasses import dataclass, field
import json
import re

try:
    from .esm_types import EsmFile, Model, ReactionSystem, Reaction, Expr, ExprNode, Equation
    from .coupling_graph import construct_coupling_graph
except ImportError:
    # For direct imports when testing
    from types import EsmFile, Model, ReactionSystem, Reaction, Expr, ExprNode, Equation
    from coupling_graph import construct_coupling_graph


def _format_chemical_name(name: str) -> str:
    """
    Format chemical names with proper Unicode subscripts.

    Converts patterns like H2O, CO2, NH4+, SO4-2 to H₂O, CO₂, NH₄⁺, SO₄²⁻
    """
    # Unicode subscript mapping
    subscripts = {'0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
                  '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉'}

    # Unicode superscript mapping for charges
    superscripts = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
                    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
                    '+': '⁺', '-': '⁻'}

    result = name

    # Handle charges first (e.g., NH4+, SO4-2)
    result = re.sub(r'([+-])(\d*)', lambda m: superscripts.get(m.group(1), m.group(1)) +
                    ''.join(superscripts.get(d, d) for d in m.group(2)), result)

    # Handle subscripts (numbers following letters, e.g., H2O -> H₂O)
    result = re.sub(r'([A-Za-z])(\d+)', lambda m: m.group(1) +
                    ''.join(subscripts.get(d, d) for d in m.group(2)), result)

    return result


@dataclass
class GraphNode:
    """A node in a graph representation."""
    id: str
    label: str
    node_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComponentNode(GraphNode):
    """A component node representing models or reaction systems."""
    def __init__(self, id: str, label: str, component_type: str, **metadata):
        super().__init__(id, _format_chemical_name(label), component_type, metadata)


@dataclass
class VariableNode(GraphNode):
    """A variable node representing mathematical variables or expressions."""
    def __init__(self, id: str, label: str, variable_type: str, **metadata):
        super().__init__(id, _format_chemical_name(label), variable_type, metadata)


@dataclass
class GraphEdge:
    """An edge in a graph representation."""
    source: str
    target: str
    label: str = ""
    edge_type: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CouplingEdge(GraphEdge):
    """An edge representing coupling between components."""
    def __init__(self, source: str, target: str, label: str = "", coupling_type: str = "coupling", **metadata):
        super().__init__(source, target, label, coupling_type, metadata)


@dataclass
class DependencyEdge(GraphEdge):
    """An edge representing mathematical dependencies."""
    def __init__(self, source: str, target: str, label: str = "", dependency_type: str = "dependency", **metadata):
        super().__init__(source, target, label, dependency_type, metadata)


@dataclass
class Graph:
    """Generic graph representation with nodes and edges."""
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dot(self) -> str:
        """Export graph to DOT format for Graphviz."""
        lines = ["digraph G {"]
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box, style=filled];")

        # Add nodes
        for node in self.nodes:
            style = self._get_dot_node_style(node.node_type)
            lines.append(f'  "{node.id}" [label="{node.label}", {style}];')

        # Add edges
        for edge in self.edges:
            edge_label = f'[label="{edge.label}"]' if edge.label else ""
            lines.append(f'  "{edge.source}" -> "{edge.target}" {edge_label};')

        lines.append("}")
        return "\n".join(lines)

    def to_mermaid(self) -> str:
        """Export graph to Mermaid format."""
        lines = ["graph TD"]

        # Add nodes with styling
        for node in self.nodes:
            shape = self._get_mermaid_node_shape(node.node_type)
            lines.append(f'  {node.id}{shape}')

        # Add edges
        for edge in self.edges:
            arrow = "-->" if not edge.label else f'-->|"{edge.label}"|'
            lines.append(f'  {edge.source} {arrow} {edge.target}')

        # Add styling
        lines.extend(self._get_mermaid_styling())

        return "\n".join(lines)

    def to_json_graph(self) -> str:
        """Export graph to JSON format."""
        data = {
            "nodes": [
                {
                    "id": node.id,
                    "label": node.label,
                    "type": node.node_type,
                    "metadata": node.metadata
                }
                for node in self.nodes
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "label": edge.label,
                    "type": edge.edge_type,
                    "metadata": edge.metadata
                }
                for edge in self.edges
            ],
            "metadata": self.metadata
        }
        return json.dumps(data, indent=2)

    def _get_dot_node_style(self, node_type: str) -> str:
        """Get DOT styling for node type."""
        styles = {
            "model": "fillcolor=lightblue",
            "reaction_system": "fillcolor=lightgreen",
            "variable": "fillcolor=lightyellow",
            "expression": "fillcolor=lightcoral, shape=ellipse",
            "operator": "fillcolor=lightgray, shape=diamond",
            "constant": "fillcolor=white"
        }
        return styles.get(node_type, "fillcolor=lightgray")

    def _get_mermaid_node_shape(self, node_type: str) -> str:
        """Get Mermaid node shape for node type."""
        shapes = {
            "model": f'["{self._find_node_by_type(node_type).label}"]',
            "reaction_system": f'("{self._find_node_by_type(node_type).label}")',
            "variable": f'{{{self._find_node_by_type(node_type).label}}}',
            "expression": f'(({self._find_node_by_type(node_type).label}))',
            "operator": f'{{{{{self._find_node_by_type(node_type).label}}}}}',
            "constant": f'[{self._find_node_by_type(node_type).label}]'
        }
        return shapes.get(node_type, f'[{self._find_node_by_type(node_type).label}]')

    def _find_node_by_type(self, node_type: str) -> GraphNode:
        """Helper to find first node of given type."""
        for node in self.nodes:
            if node.node_type == node_type:
                return node
        return GraphNode("", "", node_type)  # Fallback

    def _get_mermaid_styling(self) -> List[str]:
        """Get Mermaid styling classes."""
        return [
            "  classDef model fill:#add8e6",
            "  classDef reaction fill:#90ee90",
            "  classDef variable fill:#ffffe0",
            "  classDef expression fill:#f08080",
            "  classDef operator fill:#d3d3d3"
        ]


def component_graph(esm_file: EsmFile) -> 'Graph[ComponentNode, CouplingEdge]':
    """
    Create a component graph from an ESM file showing models, reaction systems,
    and their coupling relationships.

    Args:
        esm_file: The ESM file to analyze

    Returns:
        Graph representing the component structure and couplings with ComponentNode and CouplingEdge types
    """
    graph = Graph(metadata={"type": "component_graph", "title": "Component Graph"})

    # Add model nodes
    if esm_file.models:
        for model in esm_file.models:
            node = ComponentNode(
                id=f"model_{model.name}",
                label=model.name,
                component_type="model",
                num_variables=len(model.variables) if model.variables else 0,
                num_equations=len(model.equations) if model.equations else 0
            )
            graph.nodes.append(node)

    # Add reaction system nodes
    if esm_file.reaction_systems:
        for rs in esm_file.reaction_systems:
            node = ComponentNode(
                id=f"rs_{rs.name}",
                label=rs.name,
                component_type="reaction_system",
                num_species=len(rs.species) if rs.species else 0,
                num_reactions=len(rs.reactions) if rs.reactions else 0
            )
            graph.nodes.append(node)

    # Add coupling edges using the existing coupling graph functionality
    try:
        coupling_graph = construct_coupling_graph(esm_file)

        for edge in coupling_graph.edges:
            source_node = coupling_graph.nodes.get(edge.source_node)
            target_node = coupling_graph.nodes.get(edge.target_node)

            if source_node and target_node:
                graph_edge = CouplingEdge(
                    source=f"{source_node.type.value}_{source_node.name}",
                    target=f"{target_node.type.value}_{target_node.name}",
                    label=f"{len(edge.source_variables)} vars",
                    coupling_type="coupling",
                    coupling_type_detail=edge.coupling_type.value if hasattr(edge.coupling_type, 'value') else str(edge.coupling_type),
                    variables=edge.source_variables + edge.target_variables
                )
                graph.edges.append(graph_edge)
    except Exception:
        # If coupling graph construction fails, skip coupling edges
        pass

    return graph


def expression_graph(target: Union[EsmFile, Model, ReactionSystem, Reaction, Equation, Expr]) -> 'Graph[VariableNode, DependencyEdge]':
    """
    Create an expression graph showing the mathematical structure and dependencies.

    Args:
        target: The ESM file, model, reaction system, reaction, equation, or expression to analyze

    Returns:
        Graph representing the expression structure and mathematical dependencies with VariableNode and DependencyEdge types
    """
    graph = Graph(metadata={"type": "expression_graph", "title": "Expression Graph"})

    if isinstance(target, EsmFile):
        # Extract expressions from all models and reaction systems
        expressions = []
        if target.models:
            for model in target.models:
                expressions.extend(_extract_model_expressions(model))
        if target.reaction_systems:
            for rs in target.reaction_systems:
                expressions.extend(_extract_reaction_system_expressions(rs))

        for i, expr in enumerate(expressions):
            _add_expression_to_graph(graph, expr, f"expr_{i}")

    elif isinstance(target, Model):
        expressions = _extract_model_expressions(target)
        for i, expr in enumerate(expressions):
            _add_expression_to_graph(graph, expr, f"model_{target.name}_expr_{i}")

    elif isinstance(target, ReactionSystem):
        expressions = _extract_reaction_system_expressions(target)
        for i, expr in enumerate(expressions):
            _add_expression_to_graph(graph, expr, f"rs_{target.name}_expr_{i}")

    elif isinstance(target, Reaction):
        # Add reactants and products as nodes, rate constant as expression
        for reactant, coeff in target.reactants.items():
            reactant_id = f"reactant_{reactant}"
            _add_expression_to_graph(graph, reactant, reactant_id)
            if coeff != 1.0:
                coeff_id = f"coeff_{reactant}"
                _add_expression_to_graph(graph, coeff, coeff_id)
                graph.edges.append(DependencyEdge(coeff_id, reactant_id, "×", "coefficient"))

        for product, coeff in target.products.items():
            product_id = f"product_{product}"
            _add_expression_to_graph(graph, product, product_id)
            if coeff != 1.0:
                coeff_id = f"coeff_{product}"
                _add_expression_to_graph(graph, coeff, coeff_id)
                graph.edges.append(DependencyEdge(coeff_id, product_id, "×", "coefficient"))

        # Add rate constant if present
        if target.rate_constant is not None:
            _add_expression_to_graph(graph, target.rate_constant, "rate_constant")

    elif isinstance(target, Equation):
        _add_expression_to_graph(graph, target.lhs, "lhs")
        _add_expression_to_graph(graph, target.rhs, "rhs")
        # Connect lhs and rhs
        graph.edges.append(DependencyEdge("lhs", "rhs", "=", "equation"))

    elif isinstance(target, (ExprNode, int, float, str)):
        _add_expression_to_graph(graph, target, "root")

    return graph


def _extract_model_expressions(model: Model) -> List[Expr]:
    """Extract all expressions from a model."""
    expressions = []

    # Extract from variable expressions
    if model.variables:
        for var_name, var_info in model.variables.items():
            if hasattr(var_info, 'expression') and var_info.expression:
                expressions.append(var_info.expression)

    # Extract from equations
    if model.equations:
        for eq in model.equations:
            expressions.extend([eq.lhs, eq.rhs])

    return expressions


def _extract_reaction_system_expressions(rs: ReactionSystem) -> List[Expr]:
    """Extract all expressions from a reaction system."""
    expressions = []

    # Extract from parameters
    if rs.parameters:
        for param in rs.parameters:
            if hasattr(param, 'value') and isinstance(param.value, (ExprNode, int, float, str)):
                expressions.append(param.value)

    # Extract from reaction rate constants
    if rs.reactions:
        for reaction in rs.reactions:
            if hasattr(reaction, 'rate_constant') and reaction.rate_constant:
                expressions.append(reaction.rate_constant)

    return expressions


def _add_expression_to_graph(graph: Graph, expr: Expr, node_id: str) -> None:
    """Add an expression and its subexpressions to the graph."""
    if isinstance(expr, (int, float)):
        node = VariableNode(
            id=node_id,
            label=str(expr),
            variable_type="constant",
            value=expr,
            type=type(expr).__name__
        )
        graph.nodes.append(node)

    elif isinstance(expr, str):
        node = VariableNode(
            id=node_id,
            label=_format_chemical_name(expr),
            variable_type="variable",
            name=expr
        )
        graph.nodes.append(node)

    elif isinstance(expr, ExprNode):
        # Add operator node
        op_node = VariableNode(
            id=node_id,
            label=expr.op,
            variable_type="operator",
            operation=expr.op,
            arity=len(expr.args)
        )
        graph.nodes.append(op_node)

        # Add argument nodes and edges
        for i, arg in enumerate(expr.args):
            arg_id = f"{node_id}_arg_{i}"
            _add_expression_to_graph(graph, arg, arg_id)

            # Connect operator to argument
            edge = DependencyEdge(
                source=node_id,
                target=arg_id,
                label=f"arg{i}",
                dependency_type="operand"
            )
            graph.edges.append(edge)


# Export functions for external use
def to_dot(graph: Graph) -> str:
    """Export graph to DOT format for Graphviz visualization."""
    return graph.to_dot()


def to_mermaid(graph: Graph) -> str:
    """Export graph to Mermaid format for web-based visualization."""
    return graph.to_mermaid()


def to_json_graph(graph: Graph) -> str:
    """Export graph to JSON format for programmatic use."""
    return graph.to_json_graph()