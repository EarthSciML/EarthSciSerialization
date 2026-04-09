#!/usr/bin/env python3
"""
Test script for the newly implemented analysis and Jupyter integration features.
"""

import sys
sys.path.insert(0, 'src')

from esm_format import (
    EsmFile, Model, ReactionSystem, ModelVariable, Species, Parameter, Reaction,
    ExprNode, Equation, Metadata,
    component_graph, expression_graph, validate_units, explore, ESMEditor
)


def create_test_esm_file():
    """Create a simple test ESM file."""
    # Create a simple model
    model = Model(
        name="simple_model",
        variables={
            "x": ModelVariable(type="state", units="m", default=1.0),
            "y": ModelVariable(type="state", units="m/s", default=0.0),
            "k": ModelVariable(type="parameter", units="1/s", default=0.1)
        },
        equations=[
            Equation(lhs="x", rhs=ExprNode("*", ["k", "x"])),
            Equation(lhs="y", rhs=ExprNode("+", ["x", 1]))
        ]
    )

    # Create a simple reaction system
    rs = ReactionSystem(
        name="simple_reactions",
        species=[
            Species(name="A", units="mol/L"),
            Species(name="B", units="mol/L")
        ],
        parameters=[
            Parameter(name="k1", value=0.1, units="1/s")
        ],
        reactions=[
            Reaction(
                name="r1",
                reactants={"A": 1},
                products={"B": 1},
                rate_constant="k1"
            )
        ]
    )

    # Create ESM file
    esm_file = EsmFile(
        version="1.0",
        metadata=Metadata(title="Test ESM File", description="A test file"),
        models=[model],
        reaction_systems=[rs]
    )

    return esm_file


def test_graph_functionality():
    """Test graph generation functionality."""
    print("Testing graph functionality...")

    esm_file = create_test_esm_file()

    # Test component graph
    comp_graph = component_graph(esm_file)
    print(f"Component graph: {len(comp_graph.nodes)} nodes, {len(comp_graph.edges)} edges")

    # Test DOT export
    dot_output = comp_graph.to_dot()
    print("DOT format generated successfully")

    # Test Mermaid export
    mermaid_output = comp_graph.to_mermaid()
    print("Mermaid format generated successfully")

    # Test JSON export
    json_output = comp_graph.to_json_graph()
    print("JSON format generated successfully")

    # Test expression graph
    model = esm_file.models[0]
    expr_graph = expression_graph(model)
    print(f"Expression graph: {len(expr_graph.nodes)} nodes, {len(expr_graph.edges)} edges")


def test_unit_validation():
    """Test unit validation functionality."""
    print("\nTesting unit validation...")

    try:
        esm_file = create_test_esm_file()

        # Test unit validation
        result = validate_units(esm_file)
        print(f"Unit validation result: {'Valid' if result.is_valid else 'Invalid'}")

        if result.errors:
            print(f"Errors: {result.errors}")
        if result.warnings:
            print(f"Warnings: {result.warnings}")

        print("Unit validation completed successfully")

    except ImportError as e:
        print(f"Unit validation skipped (missing pint): {e}")


def test_editing_functionality():
    """Test editing operations."""
    print("\nTesting editing functionality...")

    esm_file = create_test_esm_file()
    editor = ESMEditor(validate_after_edit=False)  # Skip validation to avoid potential issues

    # Test adding a variable to a model
    new_var = ModelVariable(type="parameter", units="kg", default=2.0)
    result = editor.add_variable(esm_file.models[0], "mass", new_var)

    print(f"Add variable result: {'Success' if result.success else 'Failed'}")
    if result.errors:
        print(f"Errors: {result.errors}")

    # Test renaming a variable
    result = editor.rename_variable(esm_file.models[0], "x", "position")
    print(f"Rename variable result: {'Success' if result.success else 'Failed'}")
    if result.errors:
        print(f"Errors: {result.errors}")


def test_jupyter_integration():
    """Test Jupyter integration features."""
    print("\nTesting Jupyter integration...")

    esm_file = create_test_esm_file()

    # Test explorer creation
    explorer = explore(esm_file)
    print("ESM Explorer created successfully")

    # Test HTML representation (would be used in Jupyter)
    html_repr = explorer._repr_html_()
    print(f"HTML representation generated ({len(html_repr)} characters)")

    # Test method calls
    print("\nModel summary:")
    explorer.show_models()

    print("\nReaction summary:")
    explorer.show_reactions()

    print("\nGraph display:")
    explorer.show_graph("mermaid")


if __name__ == "__main__":
    print("Testing new ESM Format analysis and Jupyter integration features...\n")

    test_graph_functionality()
    test_unit_validation()
    test_editing_functionality()
    test_jupyter_integration()

    print("\nAll tests completed!")