"""
Graph representations for ESM Format structures.

Implements component_graph() and expression_graph() functions per ESM Format
Specification Section 4.8, with export capabilities to DOT, Mermaid, and JSON formats.
"""

from typing import Dict, List, Set, Union, Any, Optional
from dataclasses import dataclass, field
import json

try:
    from .types import EsmFile, Model, ReactionSystem, Expr, ExprNode, Equation
    from .coupling_graph import construct_coupling_graph
except ImportError:
    # For direct imports when testing
    from types import EsmFile, Model, ReactionSystem, Expr, ExprNode, Equation
    from coupling_graph import construct_coupling_graph


@dataclass
class GraphNode:
    """A node in a graph representation."""
    id: str
    label: str
    node_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """An edge in a graph representation."""
    source: str
    target: str
    label: str = ""
    edge_type: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)


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

    def to_json(self) -> str:
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


def component_graph(esm_file: EsmFile) -> Graph:
    """
    Create a component graph from an ESM file showing models, reaction systems,
    and their coupling relationships.

    Args:
        esm_file: The ESM file to analyze

    Returns:
        Graph representing the component structure and couplings
    """
    graph = Graph(metadata={"type": "component_graph", "title": "Component Graph"})

    # Add model nodes
    if esm_file.models:
        for model in esm_file.models:
            node = GraphNode(
                id=f"model_{model.name}",
                label=model.name,
                node_type="model",
                metadata={
                    "num_variables": len(model.variables) if model.variables else 0,
                    "num_equations": len(model.equations) if model.equations else 0
                }
            )
            graph.nodes.append(node)

    # Add reaction system nodes
    if esm_file.reaction_systems:
        for rs in esm_file.reaction_systems:
            node = GraphNode(
                id=f"rs_{rs.name}",
                label=rs.name,
                node_type="reaction_system",
                metadata={
                    "num_species": len(rs.species) if rs.species else 0,
                    "num_reactions": len(rs.reactions) if rs.reactions else 0
                }
            )
            graph.nodes.append(node)

    # Add coupling edges using the existing coupling graph functionality
    try:
        coupling_graph = construct_coupling_graph(esm_file)

        for edge in coupling_graph.edges:
            source_node = coupling_graph.nodes.get(edge.source_node)
            target_node = coupling_graph.nodes.get(edge.target_node)

            if source_node and target_node:
                graph_edge = GraphEdge(
                    source=f"{source_node.type.value}_{source_node.name}",
                    target=f"{target_node.type.value}_{target_node.name}",
                    label=f"{len(edge.source_variables)} vars",
                    edge_type="coupling",
                    metadata={
                        "coupling_type": edge.coupling_type.value if hasattr(edge.coupling_type, 'value') else str(edge.coupling_type),
                        "variables": edge.source_variables + edge.target_variables
                    }
                )
                graph.edges.append(graph_edge)
    except Exception:
        # If coupling graph construction fails, skip coupling edges
        pass

    return graph


def expression_graph(target: Union[EsmFile, Model, ReactionSystem, Expr, Equation]) -> Graph:
    """
    Create an expression graph showing the mathematical structure and dependencies.

    Args:
        target: The ESM file, model, reaction system, expression, or equation to analyze

    Returns:
        Graph representing the expression structure and mathematical dependencies
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

    elif isinstance(target, Equation):
        _add_expression_to_graph(graph, target.lhs, "lhs")
        _add_expression_to_graph(graph, target.rhs, "rhs")
        # Connect lhs and rhs
        graph.edges.append(GraphEdge("lhs", "rhs", "=", "equation"))

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
        node = GraphNode(
            id=node_id,
            label=str(expr),
            node_type="constant",
            metadata={"value": expr, "type": type(expr).__name__}
        )
        graph.nodes.append(node)

    elif isinstance(expr, str):
        node = GraphNode(
            id=node_id,
            label=expr,
            node_type="variable",
            metadata={"name": expr}
        )
        graph.nodes.append(node)

    elif isinstance(expr, ExprNode):
        # Add operator node
        op_node = GraphNode(
            id=node_id,
            label=expr.op,
            node_type="operator",
            metadata={"operation": expr.op, "arity": len(expr.args)}
        )
        graph.nodes.append(op_node)

        # Add argument nodes and edges
        for i, arg in enumerate(expr.args):
            arg_id = f"{node_id}_arg_{i}"
            _add_expression_to_graph(graph, arg, arg_id)

            # Connect operator to argument
            edge = GraphEdge(
                source=node_id,
                target=arg_id,
                label=f"arg{i}",
                edge_type="operand"
            )
            graph.edges.append(edge)