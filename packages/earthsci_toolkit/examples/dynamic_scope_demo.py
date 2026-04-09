#!/usr/bin/env python3
"""
Demonstration of dynamic scope resolution capabilities.

This script shows how to use the DynamicScopeResolver for:
1. Parameter injection at runtime
2. Context switching between different runtime environments
3. Dynamic scope creation
4. Variable overrides
"""

import sys
import os

# Add the source path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from esm_format.dynamic_scope_resolution import DynamicScopeResolver
from esm_format.types import EsmFile, Metadata


def create_demo_esm():
    """Create a demo ESM file for the demonstration."""
    metadata = Metadata(title="Dynamic Scope Demo")

    # Simple atmospheric model
    atmosphere_model = {
        'name': 'AtmosphereModel',
        'variables': {
            'temperature': {'type': 'parameter', 'units': 'K', 'default': 298.15},
            'pressure': {'type': 'parameter', 'units': 'Pa', 'default': 101325.0},
            'wind_speed': {'type': 'state', 'units': 'm/s', 'default': 5.0}
        },
        'subsystems': {
            'Chemistry': {
                'variables': {
                    'O3': {'type': 'state', 'units': 'ppb', 'default': 40.0},
                    'NO2': {'type': 'state', 'units': 'ppb', 'default': 20.0}
                }
            },
            'Dynamics': {
                'variables': {
                    'turbulence_coeff': {'type': 'parameter', 'units': 'm^2/s', 'default': 100.0}
                }
            }
        }
    }

    return EsmFile(
        version="0.1.0",
        metadata=metadata,
        models={'AtmosphereModel': atmosphere_model}
    )


def demo_basic_functionality():
    """Demonstrate basic dynamic scope functionality."""
    print("=== Basic Dynamic Scope Resolution Demo ===\n")

    esm_file = create_demo_esm()
    resolver = DynamicScopeResolver(esm_file)

    # Show initial resolution
    print("1. Base variable resolution:")
    result = resolver.resolve_variable_dynamic("AtmosphereModel.temperature")
    print(f"   AtmosphereModel.temperature = {result.resolved_value} ({result.resolution_type})")

    # Parameter injection
    print("\n2. Parameter injection:")
    resolver.inject_parameter(
        "AtmosphereModel",
        "humidity",
        65.0,
        units="percent",
        description="Injected humidity parameter",
        injector_id="demo_script"
    )

    result = resolver.resolve_variable_dynamic("AtmosphereModel.humidity")
    print(f"   AtmosphereModel.humidity = {result.resolved_value} ({result.resolution_type})")

    # Variable override
    print("\n3. Variable override:")
    resolver.override_variable("AtmosphereModel", "temperature", 305.0)
    result = resolver.resolve_variable_dynamic("AtmosphereModel.temperature")
    print(f"   AtmosphereModel.temperature = {result.resolved_value} ({result.resolution_type})")

    # Dynamic scope creation
    print("\n4. Dynamic scope creation:")
    resolver.create_dynamic_scope(
        "AtmosphereModel",
        "RuntimeDiagnostics",
        variables={
            "cpu_usage": {"type": "parameter", "value": 25.5, "units": "percent"},
            "memory_usage": {"type": "parameter", "value": 1024.0, "units": "MB"}
        },
        component_type="diagnostic"
    )

    result = resolver.resolve_variable_dynamic("AtmosphereModel.RuntimeDiagnostics.cpu_usage")
    print(f"   AtmosphereModel.RuntimeDiagnostics.cpu_usage = {result.resolved_value} ({result.resolution_type})")


def demo_context_switching():
    """Demonstrate context switching capabilities."""
    print("\n\n=== Context Switching Demo ===\n")

    esm_file = create_demo_esm()
    resolver = DynamicScopeResolver(esm_file)

    # Create multiple contexts for different scenarios
    winter_ctx = resolver.create_runtime_context(
        "Winter Conditions",
        description="Winter atmospheric conditions"
    )

    summer_ctx = resolver.create_runtime_context(
        "Summer Conditions",
        description="Summer atmospheric conditions"
    )

    # Set up winter conditions
    resolver.switch_context(winter_ctx)
    resolver.override_variable("AtmosphereModel", "temperature", 273.15)  # 0°C
    resolver.inject_parameter("AtmosphereModel", "snow_depth", 0.5, units="m")
    resolver.inject_parameter("AtmosphereModel.Chemistry", "winter_reaction_rate", 0.8, units="dimensionless")

    # Set up summer conditions
    resolver.switch_context(summer_ctx)
    resolver.override_variable("AtmosphereModel", "temperature", 308.15)  # 35°C
    resolver.inject_parameter("AtmosphereModel", "solar_radiation", 800.0, units="W/m^2")
    resolver.inject_parameter("AtmosphereModel.Chemistry", "photolysis_rate", 1.5, units="dimensionless")

    # Demonstrate switching between contexts
    print("1. Winter conditions:")
    resolver.switch_context(winter_ctx)
    temp_result = resolver.resolve_variable_dynamic("AtmosphereModel.temperature")
    snow_result = resolver.resolve_variable_dynamic("AtmosphereModel.snow_depth")
    print(f"   Temperature: {temp_result.resolved_value} K")
    print(f"   Snow depth: {snow_result.resolved_value} m")

    print("\n2. Summer conditions:")
    resolver.switch_context(summer_ctx)
    temp_result = resolver.resolve_variable_dynamic("AtmosphereModel.temperature")
    solar_result = resolver.resolve_variable_dynamic("AtmosphereModel.solar_radiation")
    print(f"   Temperature: {temp_result.resolved_value} K")
    print(f"   Solar radiation: {solar_result.resolved_value} W/m^2")

    # Show context isolation
    print("\n3. Context isolation:")
    try:
        resolver.resolve_variable_dynamic("AtmosphereModel.snow_depth")
        print("   ERROR: Should not be able to resolve winter variable in summer context!")
    except ValueError:
        print("   ✓ Cannot resolve winter-specific variable in summer context")


def demo_temporary_contexts():
    """Demonstrate temporary context usage."""
    print("\n\n=== Temporary Context Demo ===\n")

    esm_file = create_demo_esm()
    resolver = DynamicScopeResolver(esm_file)

    # Set up a temporary high-resolution context
    highres_ctx = resolver.create_runtime_context(
        "High Resolution",
        description="High resolution simulation parameters"
    )

    resolver.inject_parameter("AtmosphereModel", "grid_resolution", 1000.0, units="m", context_id=highres_ctx)
    resolver.inject_parameter("AtmosphereModel", "time_step", 10.0, units="s", context_id=highres_ctx)

    print("1. Normal resolution (default context):")
    try:
        resolver.resolve_variable_dynamic("AtmosphereModel.grid_resolution")
        print("   ERROR: Should not find grid_resolution in default context!")
    except ValueError:
        print("   ✓ grid_resolution not available in default context")

    print("\n2. Using temporary high-resolution context:")
    with resolver.temporary_context(highres_ctx) as temp_ctx:
        print(f"   Context name: {temp_ctx.name}")
        grid_result = resolver.resolve_variable_dynamic("AtmosphereModel.grid_resolution")
        time_result = resolver.resolve_variable_dynamic("AtmosphereModel.time_step")
        print(f"   Grid resolution: {grid_result.resolved_value} m")
        print(f"   Time step: {time_result.resolved_value} s")

    print("\n3. Back to normal resolution:")
    try:
        resolver.resolve_variable_dynamic("AtmosphereModel.grid_resolution")
        print("   ERROR: Should not find grid_resolution after exiting temporary context!")
    except ValueError:
        print("   ✓ Back to default context - high-res parameters not available")


def demo_runtime_statistics():
    """Show runtime statistics and monitoring."""
    print("\n\n=== Runtime Statistics Demo ===\n")

    esm_file = create_demo_esm()
    resolver = DynamicScopeResolver(esm_file)

    # Add various runtime modifications
    ctx1 = resolver.create_runtime_context("Context 1")
    ctx2 = resolver.create_runtime_context("Context 2", parent_context_id=ctx1)

    resolver.switch_context(ctx1)
    resolver.inject_parameter("AtmosphereModel", "var1", 1.0)
    resolver.inject_parameter("AtmosphereModel", "var2", 2.0)
    resolver.override_variable("AtmosphereModel", "temperature", 310.0)

    resolver.switch_context(ctx2)
    resolver.create_dynamic_scope("AtmosphereModel", "DynamicScope")
    resolver.inject_parameter("AtmosphereModel.Chemistry", "var3", 3.0)

    # Show statistics
    stats = resolver.get_runtime_statistics()
    print("Runtime Statistics:")
    print(f"  Total contexts: {stats['total_contexts']}")
    print(f"  Current context: {stats['current_context_id']}")
    print(f"  Total injections: {stats['total_injections']}")
    print(f"  Total overrides: {stats['total_overrides']}")
    print(f"  Total dynamic scopes: {stats['total_dynamic_scopes']}")

    print("\nContext Details:")
    for ctx_id, ctx_info in stats['contexts_info'].items():
        print(f"  {ctx_id}:")
        print(f"    Name: {ctx_info['name']}")
        print(f"    Injections: {ctx_info['injection_count']}")
        print(f"    Overrides: {ctx_info['override_count']}")
        print(f"    Dynamic scopes: {ctx_info['dynamic_scope_count']}")
        print(f"    Has parent: {ctx_info['has_parent']}")

    # List all contexts
    print("\nAll contexts:")
    contexts = resolver.list_contexts()
    for ctx_id, name, is_current in contexts:
        current_marker = " (current)" if is_current else ""
        print(f"  {ctx_id}: {name}{current_marker}")


if __name__ == "__main__":
    print("Dynamic Scope Resolution Demonstration")
    print("=" * 50)

    demo_basic_functionality()
    demo_context_switching()
    demo_temporary_contexts()
    demo_runtime_statistics()

    print("\n" + "=" * 50)
    print("Demo completed successfully!")