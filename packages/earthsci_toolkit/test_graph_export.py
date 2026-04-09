#!/usr/bin/env python3
"""
Test suite for graph export functionality (DOT, Mermaid, JSON formats).

Tests the graph export formats to verify they are functional as requested
in task EarthSciSerialization-guns.
"""

import json
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from esm_format.graph import (
    component_graph, expression_graph, Graph, GraphNode, GraphEdge,
    ComponentNode, VariableNode, CouplingEdge, DependencyEdge,
    to_dot, to_mermaid, to_json_graph
)
from esm_format.esm_types import (
    EsmFile, Metadata, Model, ModelVariable, Equation, ExprNode,
    ReactionSystem, Species, Parameter, Reaction
)


def create_test_esm_file():
    """Create a test ESM file with models and reaction systems for testing."""

    # Create metadata
    metadata = Metadata(
        title="Graph Export Test",
        description="Test file for graph export functionality",
        authors=["Test Suite"],
        version="1.0"
    )

    # Create a simple model with equations
    model_vars = {
        "x": ModelVariable(type="state", units="m", default=1.0),
        "y": ModelVariable(type="state", units="m/s", default=0.0),
        "k": ModelVariable(type="parameter", units="1/s", default=0.5)
    }

    # Create equations with ExprNode expressions
    dx_dt = ExprNode(op="D", args=["x"], wrt="t")
    k_times_y = ExprNode(op="*", args=["k", "y"])
    equation1 = Equation(lhs=dx_dt, rhs=k_times_y)

    dy_dt = ExprNode(op="D", args=["y"], wrt="t")
    neg_k_times_x = ExprNode(op="*", args=[ExprNode(op="-", args=["k"]), "x"])
    equation2 = Equation(lhs=dy_dt, rhs=neg_k_times_x)

    model = Model(
        name="oscillator",
        variables=model_vars,
        equations=[equation1, equation2]
    )

    # Create a reaction system
    species = [
        Species(name="A", units="mol/L"),
        Species(name="B", units="mol/L"),
        Species(name="C", units="mol/L")
    ]

    parameters = [
        Parameter(name="k1", value=0.1, units="L/(mol*s)"),
        Parameter(name="k2", value=0.05, units="1/s")
    ]

    reactions = [
        Reaction(
            name="forward",
            reactants={"A": 1.0, "B": 1.0},
            products={"C": 1.0},
            rate_constant="k1"
        ),
        Reaction(
            name="reverse",
            reactants={"C": 1.0},
            products={"A": 1.0, "B": 1.0},
            rate_constant="k2"
        )
    ]

    rs = ReactionSystem(
        name="kinetics",
        species=species,
        parameters=parameters,
        reactions=reactions
    )

    return EsmFile(
        version="0.1.0",
        metadata=metadata,
        models=[model],
        reaction_systems=[rs]
    )


def test_component_graph_creation():
    """Test that component_graph() creates graphs successfully."""
    print("Testing component graph creation...")

    esm_file = create_test_esm_file()
    graph = component_graph(esm_file)

    assert isinstance(graph, Graph), "component_graph should return a Graph instance"
    assert len(graph.nodes) > 0, "Graph should have nodes"
    assert graph.metadata.get("type") == "component_graph", "Graph should have correct metadata"

    # Check that we have model and reaction system nodes
    node_types = {node.node_type for node in graph.nodes}
    assert "model" in node_types, "Should have model nodes"
    assert "reaction_system" in node_types, "Should have reaction system nodes"

    print("✓ Component graph creation successful")


def test_expression_graph_creation():
    """Test that expression_graph() creates graphs successfully."""
    print("Testing expression graph creation...")

    esm_file = create_test_esm_file()
    graph = expression_graph(esm_file)

    assert isinstance(graph, Graph), "expression_graph should return a Graph instance"
    assert graph.metadata.get("type") == "expression_graph", "Graph should have correct metadata"

    # Should have various types of nodes for expressions
    if len(graph.nodes) > 0:
        node_types = {node.node_type for node in graph.nodes}
        print(f"  Found node types: {node_types}")

    print("✓ Expression graph creation successful")


def test_dot_export():
    """Test DOT format export functionality."""
    print("Testing DOT export...")

    esm_file = create_test_esm_file()

    # Test component graph DOT export
    comp_graph = component_graph(esm_file)
    dot_output = comp_graph.to_dot()

    assert isinstance(dot_output, str), "DOT output should be a string"
    assert "digraph G" in dot_output, "DOT output should start with digraph declaration"
    assert "}" in dot_output, "DOT output should end with closing brace"
    assert "rankdir=LR" in dot_output, "Should set left-to-right ranking"

    # Test standalone function
    dot_output2 = to_dot(comp_graph)
    assert dot_output == dot_output2, "Method and function should produce same output"

    # Test expression graph DOT export
    expr_graph = expression_graph(esm_file)
    expr_dot = expr_graph.to_dot()
    assert isinstance(expr_dot, str), "Expression DOT output should be a string"
    assert "digraph G" in expr_dot, "Expression DOT should have digraph declaration"

    print(f"✓ DOT export successful (component: {len(dot_output)} chars, expression: {len(expr_dot)} chars)")


def test_mermaid_export():
    """Test Mermaid format export functionality."""
    print("Testing Mermaid export...")

    esm_file = create_test_esm_file()

    # Test component graph Mermaid export
    comp_graph = component_graph(esm_file)
    mermaid_output = comp_graph.to_mermaid()

    assert isinstance(mermaid_output, str), "Mermaid output should be a string"
    assert "graph TD" in mermaid_output, "Mermaid output should start with graph declaration"
    assert "-->" in mermaid_output or len(comp_graph.edges) == 0, "Should have arrows if there are edges"

    # Test standalone function
    mermaid_output2 = to_mermaid(comp_graph)
    assert mermaid_output == mermaid_output2, "Method and function should produce same output"

    # Test expression graph Mermaid export
    expr_graph = expression_graph(esm_file)
    expr_mermaid = expr_graph.to_mermaid()
    assert isinstance(expr_mermaid, str), "Expression Mermaid output should be a string"
    assert "graph TD" in expr_mermaid, "Expression Mermaid should have graph declaration"

    print(f"✓ Mermaid export successful (component: {len(mermaid_output)} chars, expression: {len(expr_mermaid)} chars)")


def test_json_export():
    """Test JSON format export functionality."""
    print("Testing JSON export...")

    esm_file = create_test_esm_file()

    # Test component graph JSON export
    comp_graph = component_graph(esm_file)
    json_output = comp_graph.to_json_graph()

    assert isinstance(json_output, str), "JSON output should be a string"

    # Parse JSON to verify it's valid
    parsed = json.loads(json_output)
    assert "nodes" in parsed, "JSON should have nodes array"
    assert "edges" in parsed, "JSON should have edges array"
    assert "metadata" in parsed, "JSON should have metadata"
    assert isinstance(parsed["nodes"], list), "Nodes should be an array"
    assert isinstance(parsed["edges"], list), "Edges should be an array"

    # Verify node structure
    if len(parsed["nodes"]) > 0:
        node = parsed["nodes"][0]
        assert "id" in node, "Node should have id"
        assert "label" in node, "Node should have label"
        assert "type" in node, "Node should have type"
        assert "metadata" in node, "Node should have metadata"

    # Verify edge structure
    if len(parsed["edges"]) > 0:
        edge = parsed["edges"][0]
        assert "source" in edge, "Edge should have source"
        assert "target" in edge, "Edge should have target"
        assert "label" in edge, "Edge should have label"
        assert "type" in edge, "Edge should have type"
        assert "metadata" in edge, "Edge should have metadata"

    # Test standalone function
    json_output2 = to_json_graph(comp_graph)
    assert json_output == json_output2, "Method and function should produce same output"

    # Test expression graph JSON export
    expr_graph = expression_graph(esm_file)
    expr_json = expr_graph.to_json_graph()
    assert isinstance(expr_json, str), "Expression JSON output should be a string"
    expr_parsed = json.loads(expr_json)
    assert "nodes" in expr_parsed, "Expression JSON should have nodes"
    assert "edges" in expr_parsed, "Expression JSON should have edges"

    print(f"✓ JSON export successful (component: {len(json_output)} chars, expression: {len(expr_json)} chars)")


def test_graph_node_types():
    """Test that different node types produce different styling/formatting."""
    print("Testing graph node type handling...")

    # Create a simple graph with different node types
    graph = Graph()

    # Add different types of nodes
    nodes = [
        ComponentNode("model1", "Test Model", "model"),
        ComponentNode("rs1", "Test RS", "reaction_system"),
        VariableNode("var1", "x", "variable"),
        VariableNode("const1", "42", "constant"),
        VariableNode("op1", "+", "operator")
    ]

    for node in nodes:
        graph.nodes.append(node)

    # Test DOT styling differences
    dot_output = graph.to_dot()
    assert "fillcolor=lightblue" in dot_output, "Should have model styling"
    assert "fillcolor=lightgreen" in dot_output, "Should have reaction system styling"
    assert "fillcolor=lightyellow" in dot_output, "Should have variable styling"

    # Test Mermaid format
    mermaid_output = graph.to_mermaid()
    assert "classDef" in mermaid_output, "Should have CSS class definitions"

    # Test JSON structure
    json_output = graph.to_json_graph()
    parsed = json.loads(json_output)
    node_types = {node["type"] for node in parsed["nodes"]}
    expected_types = {"model", "reaction_system", "variable", "constant", "operator"}
    assert node_types == expected_types, f"Should have all node types, got {node_types}"

    print("✓ Node type handling successful")


def test_chemical_name_formatting():
    """Test that chemical names are formatted with proper subscripts/superscripts."""
    print("Testing chemical name formatting...")

    # Create nodes with chemical names that should be formatted
    graph = Graph()

    chemical_names = [
        ("H2O", "H₂O"),  # Water
        ("CO2", "CO₂"),  # Carbon dioxide
        ("NH4+", "NH₄⁺"),  # Ammonium
        ("SO4-2", "SO₄⁻²"),  # Sulfate
        ("Ca2+", "Ca₂⁺"),  # Calcium ion
    ]

    for original, expected in chemical_names:
        node = VariableNode(f"chem_{original}", original, "variable")
        graph.nodes.append(node)
        assert node.label == expected, f"Expected {expected}, got {node.label}"

    print("✓ Chemical name formatting successful")


def test_edge_types():
    """Test that different edge types are handled correctly."""
    print("Testing edge type handling...")

    graph = Graph()

    # Add nodes
    graph.nodes.extend([
        GraphNode("n1", "Node 1", "test"),
        GraphNode("n2", "Node 2", "test"),
        GraphNode("n3", "Node 3", "test")
    ])

    # Add different types of edges
    edges = [
        CouplingEdge("n1", "n2", "coupling_label", "coupling"),
        DependencyEdge("n2", "n3", "depends", "dependency"),
        GraphEdge("n1", "n3", "generic", "default")
    ]

    for edge in edges:
        graph.edges.append(edge)

    # Test JSON export includes edge types
    json_output = graph.to_json_graph()
    parsed = json.loads(json_output)

    edge_types = {edge["type"] for edge in parsed["edges"]}
    expected_types = {"coupling", "dependency", "default"}
    assert edge_types == expected_types, f"Should have all edge types, got {edge_types}"

    # Test DOT includes edge labels
    dot_output = graph.to_dot()
    assert "coupling_label" in dot_output, "Should include edge labels"
    assert "depends" in dot_output, "Should include edge labels"

    print("✓ Edge type handling successful")


def main():
    """Run all graph export tests."""
    print("Graph Export Functionality Test Suite")
    print("=" * 50)

    try:
        # Basic functionality tests
        test_component_graph_creation()
        test_expression_graph_creation()

        # Export format tests
        test_dot_export()
        test_mermaid_export()
        test_json_export()

        # Advanced feature tests
        test_graph_node_types()
        test_chemical_name_formatting()
        test_edge_types()

        print("\n" + "=" * 50)
        print("🎉 ALL GRAPH EXPORT TESTS PASSED!")
        print("\nVerified functionality:")
        print("  • DOT format export for Graphviz visualization")
        print("  • Mermaid format export for web-based visualization")
        print("  • JSON format export for programmatic use")
        print("  • Component graph generation from ESM files")
        print("  • Expression graph generation from ESM files")
        print("  • Chemical name formatting with Unicode subscripts/superscripts")
        print("  • Node type styling and formatting")
        print("  • Edge type handling and labeling")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())