#!/usr/bin/env python3
"""
Demonstration of coupling variable matching algorithm.

This script shows how the coupling variable matching algorithm works
to validate compatibility between variables in different model components.
"""

from esm_format.coupling_graph import match_coupling_variables, validate_coupling_variables
from esm_format.coupling_graph import CouplingGraph, CouplingNode, CouplingEdge, NodeType
from esm_format.types import (
    Model, ReactionSystem, EsmFile, Metadata,
    ModelVariable, Species, Parameter, CouplingType
)


def create_example_models():
    """Create example models for demonstration."""

    # Atmospheric physics model
    atmosphere_model = Model(
        name="AtmospherePhysics",
        variables={
            "temperature": ModelVariable(
                type="state",
                units="kelvin",
                description="Air temperature"
            ),
            "pressure": ModelVariable(
                type="state",
                units="pascal",
                description="Air pressure"
            ),
            "wind_velocity": ModelVariable(
                type="state",
                units="meter/second",
                description="Wind velocity"
            )
        }
    )

    # Ocean physics model
    ocean_model = Model(
        name="OceanPhysics",
        variables={
            "sea_surface_temp": ModelVariable(
                type="state",
                units="celsius",
                description="Sea surface temperature"
            ),
            "salinity": ModelVariable(
                type="state",
                units="gram/kilogram",
                description="Sea water salinity"
            ),
            "current_speed": ModelVariable(
                type="state",
                units="kilometer/hour",
                description="Ocean current speed"
            )
        }
    )

    # Atmospheric chemistry reaction system
    chemistry_system = ReactionSystem(
        name="AtmosphericChemistry",
        species=[
            Species(
                name="O3",
                formula="O3",
                units="mol/meter**3",
                description="Ozone concentration"
            ),
            Species(
                name="NO2",
                formula="NO2",
                units="mol/meter**3",
                description="Nitrogen dioxide concentration"
            )
        ],
        parameters=[
            Parameter(
                name="k_photo",
                value=1e-5,
                units="1/second",
                description="Photolysis rate constant"
            )
        ]
    )

    return atmosphere_model, ocean_model, chemistry_system


def demonstrate_variable_matching():
    """Demonstrate various variable matching scenarios."""

    print("=" * 60)
    print("COUPLING VARIABLE MATCHING ALGORITHM DEMONSTRATION")
    print("=" * 60)
    print()

    atmosphere_model, ocean_model, chemistry_system = create_example_models()

    # Test Case 1: Compatible coupling with unit conversion
    print("Test Case 1: Compatible coupling with unit conversion")
    print("-" * 50)

    result = match_coupling_variables(
        "temperature", "sea_surface_temp",
        atmosphere_model, ocean_model,
        CouplingType.DIRECT
    )

    print(f"Atmosphere.temperature -> Ocean.sea_surface_temp")
    print(f"Compatible: {result.is_compatible}")
    print(f"Unit conversion factor: {result.unit_conversion_factor}")
    print(f"Conversion: {result.conversion_expression}")
    if result.warnings:
        print(f"Warnings: {', '.join(result.warnings)}")
    print()

    # Test Case 2: Incompatible coupling (different dimensions)
    print("Test Case 2: Incompatible coupling (different dimensions)")
    print("-" * 50)

    result = match_coupling_variables(
        "temperature", "salinity",
        atmosphere_model, ocean_model,
        CouplingType.DIRECT
    )

    print(f"Atmosphere.temperature -> Ocean.salinity")
    print(f"Compatible: {result.is_compatible}")
    if result.errors:
        print(f"Errors: {', '.join(result.errors)}")
    print()

    # Test Case 3: Cross-component type coupling (species to state)
    print("Test Case 3: Cross-component type coupling (species to state)")
    print("-" * 50)

    result = match_coupling_variables(
        "O3", "temperature",
        chemistry_system, atmosphere_model,
        CouplingType.INTERPOLATED
    )

    print(f"Chemistry.O3 -> Atmosphere.temperature")
    print(f"Compatible: {result.is_compatible}")
    if result.errors:
        print(f"Errors: {', '.join(result.errors)}")
    if result.warnings:
        print(f"Warnings: {', '.join(result.warnings)}")
    print()

    # Test Case 4: Feedback coupling with warnings
    print("Test Case 4: Feedback coupling with warnings")
    print("-" * 50)

    result = match_coupling_variables(
        "wind_velocity", "current_speed",
        atmosphere_model, ocean_model,
        CouplingType.FEEDBACK
    )

    print(f"Atmosphere.wind_velocity <-> Ocean.current_speed")
    print(f"Compatible: {result.is_compatible}")
    print(f"Unit conversion factor: {result.unit_conversion_factor}")
    if result.warnings:
        print(f"Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    print()

    # Test Case 5: Incompatible type coupling (state to parameter)
    print("Test Case 5: Incompatible type coupling (state to parameter)")
    print("-" * 50)

    result = match_coupling_variables(
        "temperature", "k_photo",
        atmosphere_model, chemistry_system,
        CouplingType.DIRECT
    )

    print(f"Atmosphere.temperature -> Chemistry.k_photo")
    print(f"Compatible: {result.is_compatible}")
    print(f"Type compatible: {result.type_compatibility}")
    print(f"Unit compatible: {result.unit_compatibility}")
    if result.errors:
        print(f"Errors:")
        for error in result.errors:
            print(f"  - {error}")
    print()


def demonstrate_full_validation():
    """Demonstrate full coupling graph validation."""

    print("=" * 60)
    print("FULL COUPLING GRAPH VALIDATION")
    print("=" * 60)
    print()

    atmosphere_model, ocean_model, chemistry_system = create_example_models()

    # Create ESM file
    esm_file = EsmFile(
        version="0.1.0",
        metadata=Metadata(
            title="Climate System Demo",
            description="Demonstration of coupled climate system components"
        ),
        models=[atmosphere_model, ocean_model],
        reaction_systems=[chemistry_system]
    )

    # Create coupling graph
    graph = CouplingGraph()

    # Add nodes
    atm_node = CouplingNode(
        id="model:AtmospherePhysics",
        name="AtmospherePhysics",
        type=NodeType.MODEL,
        variables=list(atmosphere_model.variables.keys())
    )

    ocean_node = CouplingNode(
        id="model:OceanPhysics",
        name="OceanPhysics",
        type=NodeType.MODEL,
        variables=list(ocean_model.variables.keys())
    )

    chem_node = CouplingNode(
        id="reaction_system:AtmosphericChemistry",
        name="AtmosphericChemistry",
        type=NodeType.REACTION_SYSTEM,
        variables=["O3", "NO2", "k_photo"]
    )

    graph.add_node(atm_node)
    graph.add_node(ocean_node)
    graph.add_node(chem_node)

    # Add coupling edges
    edges = [
        # Compatible coupling: atmosphere-ocean temperature exchange
        CouplingEdge(
            source_node="model:AtmospherePhysics",
            target_node="model:OceanPhysics",
            source_variables=["temperature"],
            target_variables=["sea_surface_temp"],
            coupling_type=CouplingType.DIRECT
        ),
        # Compatible coupling with conversion: wind-ocean current
        CouplingEdge(
            source_node="model:AtmospherePhysics",
            target_node="model:OceanPhysics",
            source_variables=["wind_velocity"],
            target_variables=["current_speed"],
            coupling_type=CouplingType.INTERPOLATED
        ),
        # Incompatible coupling: temperature to reaction rate
        CouplingEdge(
            source_node="model:AtmospherePhysics",
            target_node="reaction_system:AtmosphericChemistry",
            source_variables=["temperature"],
            target_variables=["k_photo"],
            coupling_type=CouplingType.DIRECT
        )
    ]

    for edge in edges:
        graph.add_edge(edge)

    # Validate the complete coupling system
    is_valid, errors, detailed_results = validate_coupling_variables(
        graph, esm_file, detailed=True
    )

    print(f"Overall system validity: {is_valid}")
    print(f"Number of coupling validations: {len(detailed_results)}")
    print()

    # Show detailed results
    for i, result in enumerate(detailed_results, 1):
        edge = edges[i-1]
        print(f"Coupling {i}: {edge.source_node}.{edge.source_variables[0]} -> "
              f"{edge.target_node}.{edge.target_variables[0]}")
        print(f"  Compatible: {result.is_compatible}")
        if result.unit_conversion_factor:
            print(f"  Unit conversion: {result.unit_conversion_factor}")
        if result.errors:
            print(f"  Errors: {', '.join(result.errors)}")
        if result.warnings:
            print(f"  Warnings: {', '.join(result.warnings)}")
        print()

    # Show overall system errors
    if errors:
        print("System-level errors:")
        for error in errors:
            print(f"  - {error}")


if __name__ == "__main__":
    demonstrate_variable_matching()
    print()
    demonstrate_full_validation()