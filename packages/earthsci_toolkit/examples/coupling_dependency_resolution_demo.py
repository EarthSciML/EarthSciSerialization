#!/usr/bin/env python3
"""
Demonstration of the Coupling Dependency Resolution Algorithm

This script demonstrates the hierarchical scoped reference resolution algorithm
implemented for ESM Format. It shows how the algorithm can resolve complex
dot-notation references like 'AtmosphereModel.Chemistry.FastReactions.k1'
through nested subsystem hierarchies.
"""

from esm_format.coupling_graph import ScopedReferenceResolver, resolve_coupling_dependencies
from esm_format.types import EsmFile, Metadata


def create_demo_esm_file():
    """Create a demonstration ESM file with hierarchical components."""
    metadata = Metadata(title="Coupling Resolution Demo")

    # Create atmospheric model with nested subsystems
    atmosphere_model = {
        'variables': {
            'pressure': {'type': 'parameter', 'units': 'Pa', 'default': 101325.0},
            'temperature': {'type': 'parameter', 'units': 'K', 'default': 298.15}
        },
        'subsystems': {
            'Chemistry': {
                'variables': {
                    'O3': {'type': 'state', 'units': 'mol/mol', 'default': 40e-9},
                    'temperature': {'type': 'parameter', 'units': 'K', 'default': 298.15}
                },
                'subsystems': {
                    'FastReactions': {
                        'variables': {
                            'k1': {'type': 'parameter', 'units': '1/s', 'default': 1e-5},
                            'k2': {'type': 'parameter', 'units': 'cm^3/molec/s', 'default': 1.8e-12}
                        }
                    }
                }
            },
            'Transport': {
                'variables': {
                    'wind_speed': {'type': 'parameter', 'units': 'm/s', 'default': 5.0}
                },
                'subsystems': {
                    'Advection': {
                        'variables': {
                            'u_wind': {'type': 'parameter', 'units': 'm/s', 'default': 3.0}
                        }
                    }
                }
            }
        }
    }

    # Create data loader with subsystem
    met_data = {
        'type': 'gridded_data',
        'loader_id': 'WRF',
        'provides': {'temperature': {'units': 'K'}, 'pressure': {'units': 'Pa'}},
        'subsystems': {
            'QualityControl': {
                'variables': {
                    'flag': {'type': 'parameter', 'units': 'dimensionless', 'default': 1.0}
                }
            }
        }
    }

    # Create operator with subsystem
    emissions_operator = {
        'operator_id': 'MEGAN',
        'subsystems': {
            'TemperatureDependence': {
                'variables': {
                    'beta': {'type': 'parameter', 'units': '1/K', 'default': 0.09}
                }
            }
        }
    }

    esm_file = EsmFile(
        version="0.1.0",
        metadata=metadata,
        models={'AtmosphereModel': atmosphere_model},
        data_loaders={'MeteorologicalData': met_data},
        operators={'BiogenicEmissions': emissions_operator}
    )

    return esm_file


def demo_scoped_reference_resolution():
    """Demonstrate scoped reference resolution capabilities."""
    print("=" * 60)
    print("ESM Format Coupling Dependency Resolution Algorithm Demo")
    print("=" * 60)
    print()

    esm_file = create_demo_esm_file()
    resolver = ScopedReferenceResolver(esm_file)

    # Test cases from the coupling resolution algorithm specification
    test_cases = [
        {
            "reference": "AtmosphereModel.Chemistry",
            "description": "Two-level system reference"
        },
        {
            "reference": "AtmosphereModel.Chemistry.temperature",
            "description": "Three-level variable reference"
        },
        {
            "reference": "AtmosphereModel.Chemistry.FastReactions.k1",
            "description": "Four-level deep nesting"
        },
        {
            "reference": "AtmosphereModel.Transport.Advection.u_wind",
            "description": "Different subsystem branch"
        },
        {
            "reference": "MeteorologicalData.QualityControl.flag",
            "description": "Data loader subsystem"
        },
        {
            "reference": "BiogenicEmissions.TemperatureDependence.beta",
            "description": "Operator subsystem"
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {case['description']}")
        print(f"Reference: '{case['reference']}'")

        try:
            result = resolver.resolve_reference(case['reference'])

            print(f"✓ Resolution successful!")
            print(f"  Component Type: {result.component_type}")
            print(f"  Path: {' -> '.join(result.path)}")
            if result.target:
                print(f"  Target Variable: {result.target}")
                if result.resolved_variable:
                    units = result.resolved_variable.get('units', 'N/A')
                    default = result.resolved_variable.get('default', 'N/A')
                    print(f"  Variable Units: {units}")
                    print(f"  Default Value: {default}")
            else:
                print(f"  Target: System reference (no specific variable)")

        except Exception as e:
            print(f"✗ Resolution failed: {e}")

        print()

    print("Algorithm Steps Demonstration:")
    print("-" * 30)

    # Show step-by-step algorithm execution for one case
    reference = "AtmosphereModel.Chemistry.FastReactions.k1"
    print(f"Resolving: '{reference}'")

    segments = reference.split('.')
    print(f"1. Split on '.' → {segments}")
    print(f"2. Final segment: '{segments[-1]}' (variable name)")
    print(f"3. Path: {segments[:-1]} (hierarchy to walk)")
    print(f"4. Find '{segments[0]}' in top-level models section")
    print(f"5. Find '{segments[1]}' in {segments[0]}.subsystems")
    print(f"6. Find '{segments[2]}' in {segments[1]}.subsystems")
    print(f"7. Find '{segments[3]}' in {segments[2]}.variables")
    print(f"8. ✓ Resolution complete!")

    result = resolver.resolve_reference(reference)
    print(f"Final result: {result.component_type}:{'.'.join(result.path)}.{result.target}")


def demo_error_cases():
    """Demonstrate error handling for invalid references."""
    print("\n" + "=" * 40)
    print("Error Handling Demonstration")
    print("=" * 40)
    print()

    esm_file = create_demo_esm_file()
    resolver = ScopedReferenceResolver(esm_file)

    error_cases = [
        {
            "reference": "NonExistentModel.Chemistry.O3",
            "description": "Invalid top-level component"
        },
        {
            "reference": "AtmosphereModel.NonExistentSub.O3",
            "description": "Invalid subsystem"
        },
        {
            "reference": "AtmosphereModel.Chemistry.NonExistentVar",
            "description": "Invalid variable"
        },
        {
            "reference": "single",
            "description": "Invalid reference format"
        }
    ]

    for i, case in enumerate(error_cases, 1):
        print(f"Error Case {i}: {case['description']}")
        print(f"Reference: '{case['reference']}'")

        try:
            result = resolver.resolve_reference(case['reference'])
            print(f"Unexpected success: {result}")
        except ValueError as e:
            print(f"✓ Correctly caught error: {e}")
        except Exception as e:
            print(f"! Unexpected error type: {e}")

        print()


if __name__ == "__main__":
    demo_scoped_reference_resolution()
    demo_error_cases()

    print("\n" + "=" * 60)
    print("Demo complete! The coupling dependency resolution algorithm")
    print("successfully implements hierarchical scoped reference resolution")
    print("for ESM Format components with full error handling.")
    print("=" * 60)