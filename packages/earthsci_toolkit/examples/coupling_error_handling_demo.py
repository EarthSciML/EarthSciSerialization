#!/usr/bin/env python3
"""
Coupling Error Handling and Recovery Demo

This example demonstrates the robust coupling error handling system
with realistic Earth system model coupling scenarios that can fail
in various ways and how the system recovers.
"""

import sys
import os
import time
import math
import json
from typing import Dict, Tuple, Optional, List

# Add the package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from esm_format.coupling_error_handling import (
    create_robust_coupling_iterator,
    create_fault_tolerant_iterator,
    RecoveryConfig,
    ExecutionMode,
    RecoveryStrategy,
    CouplingErrorType
)
from esm_format.coupling_iteration import ConvergenceConfig, ConvergenceMethod
from esm_format.types import EsmFile, Metadata


def create_earth_system_esm() -> EsmFile:
    """Create a representative Earth system model ESM file."""
    metadata = Metadata(
        title="Earth System Coupling Error Handling Demo",
        description="Demonstrates robust coupling with atmospheric-ocean-land interactions"
    )

    return EsmFile(
        version="0.1.0",
        metadata=metadata,
        models=[],  # Simplified for demo
        reaction_systems=[],
        couplings=[]
    )


def atmospheric_ocean_coupling(variables: Dict[str, float], **kwargs) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
    """
    Realistic atmospheric-ocean coupling function that can exhibit various failure modes.

    Variables:
    - sea_surface_temp: Sea surface temperature (K)
    - air_temp: Air temperature (K)
    - wind_speed: Wind speed (m/s)
    - heat_flux: Surface heat flux (W/m²)
    """
    sea_surface_temp = variables.get('sea_surface_temp', 288.0)  # ~15°C
    air_temp = variables.get('air_temp', 285.0)  # ~12°C
    wind_speed = variables.get('wind_speed', 5.0)  # 5 m/s
    heat_flux = variables.get('heat_flux', 0.0)

    # Simulate coupling iteration counter for intermittent failures
    iteration = kwargs.get('iteration_count', 0)

    # Introduce realistic failure modes
    if iteration == 3:
        # Simulate numerical instability in heat flux calculation
        raise FloatingPointError("Heat flux calculation became unstable")

    if iteration == 7:
        # Simulate communication failure between atmosphere and ocean models
        raise ConnectionError("Inter-model communication timeout")

    if sea_surface_temp < 200 or sea_surface_temp > 400:
        # Temperature out of reasonable bounds
        raise ValueError(f"Sea surface temperature {sea_surface_temp} K is physically unrealistic")

    if wind_speed < 0:
        # Invalid wind speed
        raise ValueError(f"Wind speed cannot be negative: {wind_speed}")

    # Atmospheric-ocean coupling equations (simplified)
    try:
        # Heat exchange between atmosphere and ocean
        temp_diff = air_temp - sea_surface_temp
        new_heat_flux = 20.0 * temp_diff * (1 + 0.1 * wind_speed)  # Simplified heat transfer

        # Ocean temperature response
        ocean_thermal_inertia = 4.18e6  # J/(m³·K) - simplified
        new_sea_surface_temp = sea_surface_temp + 0.001 * new_heat_flux / ocean_thermal_inertia

        # Atmospheric temperature response
        atmospheric_heat_capacity = 1005.0  # J/(kg·K) for air
        new_air_temp = air_temp - 0.002 * new_heat_flux / atmospheric_heat_capacity

        # Wind speed evolution (simplified momentum transfer)
        new_wind_speed = wind_speed + 0.1 * math.tanh(temp_diff / 10.0)

        # Apply physical constraints
        new_sea_surface_temp = max(271.0, min(350.0, new_sea_surface_temp))  # Keep reasonable
        new_air_temp = max(200.0, min(320.0, new_air_temp))
        new_wind_speed = max(0.0, min(50.0, new_wind_speed))

        updated_variables = {
            'sea_surface_temp': new_sea_surface_temp,
            'air_temp': new_air_temp,
            'wind_speed': new_wind_speed,
            'heat_flux': new_heat_flux
        }

        residuals = {
            'sea_surface_temp': new_sea_surface_temp - sea_surface_temp,
            'air_temp': new_air_temp - air_temp,
            'wind_speed': new_wind_speed - wind_speed,
            'heat_flux': new_heat_flux - heat_flux
        }

        return updated_variables, residuals

    except (OverflowError, ZeroDivisionError) as e:
        # Convert numerical errors to more specific error types
        raise FloatingPointError(f"Numerical instability in atmospheric-ocean coupling: {e}")


def land_atmosphere_coupling(variables: Dict[str, float], **kwargs) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
    """
    Land-atmosphere coupling with potential memory issues for large systems.

    Variables:
    - soil_moisture: Soil moisture content (fraction)
    - air_temp: Air temperature (K)
    - precipitation: Precipitation rate (mm/day)
    - evapotranspiration: Evapotranspiration rate (mm/day)
    """
    soil_moisture = variables.get('soil_moisture', 0.3)
    air_temp = variables.get('air_temp', 285.0)
    precipitation = variables.get('precipitation', 2.0)
    evapotranspiration = variables.get('evapotranspiration', 3.0)

    # Simulate memory pressure (in real systems, this might be from large grid computations)
    iteration = kwargs.get('iteration_count', 0)
    if iteration == 12:
        # Simulate memory pressure
        raise MemoryError("Insufficient memory for land surface model computation")

    # Simulate timeout for complex vegetation dynamics
    if iteration == 15:
        time.sleep(0.05)  # Simulate slow computation
        raise TimeoutError("Vegetation dynamics computation exceeded time limit")

    try:
        # Land-atmosphere feedback
        # Evapotranspiration depends on soil moisture and temperature
        potential_et = 0.1 * (air_temp - 273.15) * (1 + soil_moisture)
        actual_et = min(potential_et, soil_moisture * 10.0)  # Limited by soil moisture

        # Soil moisture balance
        new_soil_moisture = soil_moisture + 0.1 * (precipitation - actual_et) / 100.0
        new_soil_moisture = max(0.05, min(0.95, new_soil_moisture))  # Physical limits

        # Temperature feedback (evapotranspiration cools the surface)
        cooling_effect = actual_et * 0.5
        new_air_temp = air_temp - cooling_effect

        # Precipitation feedback (simplified)
        humidity_effect = soil_moisture * 2.0
        new_precipitation = precipitation * (1 + 0.1 * math.sin(humidity_effect))
        new_precipitation = max(0.0, new_precipitation)

        updated_variables = {
            'soil_moisture': new_soil_moisture,
            'air_temp': new_air_temp,
            'precipitation': new_precipitation,
            'evapotranspiration': actual_et
        }

        residuals = {
            'soil_moisture': new_soil_moisture - soil_moisture,
            'air_temp': new_air_temp - air_temp,
            'precipitation': new_precipitation - precipitation,
            'evapotranspiration': actual_et - evapotranspiration
        }

        return updated_variables, residuals

    except (ValueError, OverflowError) as e:
        raise RuntimeError(f"Land-atmosphere coupling failed: {e}")


def robust_earth_system_coupling(variables: Dict[str, float], **kwargs) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
    """
    Combined Earth system coupling that integrates atmosphere, ocean, and land models.
    """
    # Extract variables for different components
    ocean_vars = {k: v for k, v in variables.items()
                 if k in ['sea_surface_temp', 'air_temp', 'wind_speed', 'heat_flux']}
    land_vars = {k: v for k, v in variables.items()
                if k in ['soil_moisture', 'air_temp', 'precipitation', 'evapotranspiration']}

    iteration = kwargs.get('iteration_count', 0)
    kwargs['iteration_count'] = iteration

    updated_variables = {}
    residuals = {}

    try:
        # Atmosphere-ocean coupling
        if ocean_vars:
            ocean_updated, ocean_residuals = atmospheric_ocean_coupling(ocean_vars, **kwargs)
            updated_variables.update(ocean_updated)
            residuals.update(ocean_residuals)

        # Land-atmosphere coupling (shares air_temp with ocean component)
        if land_vars:
            # Use updated air temperature from ocean coupling if available
            if 'air_temp' in updated_variables:
                land_vars['air_temp'] = updated_variables['air_temp']

            land_updated, land_residuals = land_atmosphere_coupling(land_vars, **kwargs)

            # Average air temperature if both components computed it
            if 'air_temp' in updated_variables and 'air_temp' in land_updated:
                updated_variables['air_temp'] = 0.5 * (updated_variables['air_temp'] + land_updated['air_temp'])
                residuals['air_temp'] = 0.5 * (residuals['air_temp'] + land_residuals['air_temp'])
            else:
                updated_variables.update({k: v for k, v in land_updated.items() if k != 'air_temp'})
                residuals.update({k: v for k, v in land_residuals.items() if k != 'air_temp'})

        return updated_variables, residuals

    except Exception as e:
        # Re-raise with component information
        component = "unknown"
        if "heat flux" in str(e).lower():
            component = "ocean"
        elif "soil" in str(e).lower() or "vegetation" in str(e).lower():
            component = "land"
        elif "atmospheric" in str(e).lower():
            component = "atmosphere"

        raise type(e)(f"[{component}] {str(e)}")


def demo_basic_error_recovery():
    """Demonstrate basic error recovery capabilities."""
    print("=" * 80)
    print("Demo 1: Basic Error Recovery in Earth System Coupling")
    print("=" * 80)

    # Create recovery configuration
    recovery_config = RecoveryConfig(
        max_retry_attempts=3,
        timeout_seconds=30.0,
        enable_partial_execution=True,
        default_values={
            'sea_surface_temp': 288.0,
            'air_temp': 285.0,
            'wind_speed': 5.0,
            'heat_flux': 0.0,
            'soil_moisture': 0.3,
            'precipitation': 2.0,
            'evapotranspiration': 3.0
        },
        variable_bounds={
            'sea_surface_temp': (271.0, 350.0),
            'air_temp': (200.0, 320.0),
            'wind_speed': (0.0, 50.0),
            'soil_moisture': (0.05, 0.95)
        },
        fallback_strategies=[
            RecoveryStrategy.RETRY_WITH_RELAXATION,
            RecoveryStrategy.FALLBACK_VALUES,
            RecoveryStrategy.PARTIAL_EXECUTION
        ]
    )

    # Create robust coupling iterator
    iterator = create_robust_coupling_iterator(
        recovery_config=recovery_config,
        execution_mode=ExecutionMode.BEST_EFFORT
    )

    # Initial Earth system state
    initial_variables = {
        'sea_surface_temp': 288.0,  # 15°C
        'air_temp': 285.0,          # 12°C
        'wind_speed': 5.0,          # 5 m/s
        'heat_flux': 0.0,
        'soil_moisture': 0.3,       # 30%
        'precipitation': 2.0,       # 2 mm/day
        'evapotranspiration': 3.0   # 3 mm/day
    }

    esm_file = create_earth_system_esm()

    print(f"Initial state: {initial_variables}")
    print("\nRunning robust coupling iteration...")

    # Track iterations for failure injection
    iteration_counter = {'count': 0}

    def tracked_coupling_function(variables, **kwargs):
        kwargs['iteration_count'] = iteration_counter['count']
        iteration_counter['count'] += 1
        return robust_earth_system_coupling(variables, **kwargs)

    start_time = time.time()
    result, diagnostic = iterator.iterate_coupling_robust(
        esm_file=esm_file,
        initial_variables=initial_variables,
        coupling_function=tracked_coupling_function
    )
    execution_time = time.time() - start_time

    print(f"\nResults:")
    print(f"  Converged: {result.converged}")
    print(f"  Total iterations: {result.total_iterations}")
    print(f"  Execution time: {execution_time:.2f} seconds")
    print(f"  Final state: {result.final_state.variables}")

    print(f"\nDiagnostic Summary:")
    print(f"  Errors encountered: {len(diagnostic.errors)}")
    print(f"  Warnings: {len(diagnostic.warnings)}")
    print(f"  Recovery attempts: {diagnostic.recovery_summary}")

    if diagnostic.errors:
        print(f"\nError Details:")
        for i, error in enumerate(diagnostic.errors[:3]):  # Show first 3 errors
            print(f"  {i+1}. {error.message}")

    if diagnostic.recommendations:
        print(f"\nRecommendations:")
        for i, rec in enumerate(diagnostic.recommendations[:3]):  # Show first 3
            print(f"  {i+1}. {rec}")

    print("\n" + "✓ Basic error recovery demo completed" + "\n")


def demo_fault_tolerant_simulation():
    """Demonstrate fault-tolerant simulation for production use."""
    print("=" * 80)
    print("Demo 2: Fault-Tolerant Earth System Simulation")
    print("=" * 80)

    # Create production-ready fault-tolerant iterator
    iterator = create_fault_tolerant_iterator(
        max_iterations=200,
        tolerance=1e-4,
        timeout_seconds=60.0
    )

    # Realistic initial conditions
    initial_variables = {
        'sea_surface_temp': 290.0,  # Warmer ocean (17°C)
        'air_temp': 288.0,          # 15°C
        'wind_speed': 8.0,          # 8 m/s
        'heat_flux': 50.0,          # Initial heat flux
        'soil_moisture': 0.4,       # 40% soil moisture
        'precipitation': 5.0,       # 5 mm/day
        'evapotranspiration': 4.0   # 4 mm/day
    }

    esm_file = create_earth_system_esm()

    print("Production Simulation Configuration:")
    print(f"  Max iterations: 200")
    print(f"  Tolerance: 1e-4")
    print(f"  Timeout: 60 seconds")
    print(f"  All recovery strategies enabled")

    print(f"\nInitial conditions: {initial_variables}")

    # Track iterations
    iteration_counter = {'count': 0}

    def production_coupling_function(variables, **kwargs):
        kwargs['iteration_count'] = iteration_counter['count']
        iteration_counter['count'] += 1
        return robust_earth_system_coupling(variables, **kwargs)

    print("\nRunning fault-tolerant simulation...")
    start_time = time.time()

    result, diagnostic = iterator.iterate_coupling_robust(
        esm_file=esm_file,
        initial_variables=initial_variables,
        coupling_function=production_coupling_function
    )

    execution_time = time.time() - start_time

    print(f"\nSimulation Results:")
    print(f"  Status: {'SUCCESS' if result.converged else 'FAILED'}")
    print(f"  Iterations: {result.total_iterations}")
    print(f"  Execution time: {execution_time:.2f} seconds")
    print(f"  Convergence reason: {result.convergence_reason}")

    print(f"\nFinal Earth System State:")
    for var, value in result.final_state.variables.items():
        if 'temp' in var:
            celsius = value - 273.15
            print(f"  {var}: {value:.2f} K ({celsius:.2f} °C)")
        elif var == 'soil_moisture':
            percent = value * 100
            print(f"  {var}: {value:.3f} ({percent:.1f}%)")
        else:
            print(f"  {var}: {value:.2f}")

    print(f"\nRobustness Metrics:")
    print(f"  Total errors handled: {len(diagnostic.errors)}")
    print(f"  Recovery success rate: {len([e for e in diagnostic.errors if hasattr(e, 'recovery_attempts') and any(attempt['success'] for attempt in e.recovery_attempts)]) / max(1, len(diagnostic.errors)) * 100:.1f}%")
    print(f"  Performance: {diagnostic.performance_metrics.get('average_time_per_iteration', 0)*1000:.2f} ms/iteration")

    # Export diagnostic report
    report_file = 'earth_system_diagnostic_report.json'
    with open(report_file, 'w') as f:
        f.write(diagnostic.export_json())
    print(f"  Detailed report saved to: {report_file}")

    print("\n" + "✓ Fault-tolerant simulation demo completed" + "\n")


def demo_partial_execution_resilience():
    """Demonstrate partial execution when some components fail."""
    print("=" * 80)
    print("Demo 3: Partial Execution Resilience")
    print("=" * 80)

    # Configure for partial execution with essential components
    recovery_config = RecoveryConfig(
        enable_partial_execution=True,
        essential_components=['air_temp', 'sea_surface_temp'],  # Atmosphere and ocean critical
        fallback_strategies=[RecoveryStrategy.PARTIAL_EXECUTION],
        default_values={
            'soil_moisture': 0.3,
            'precipitation': 2.0,
            'evapotranspiration': 3.0
        }
    )

    iterator = create_robust_coupling_iterator(
        recovery_config=recovery_config,
        execution_mode=ExecutionMode.ESSENTIAL_ONLY
    )

    def failing_land_coupling(variables: Dict[str, float], **kwargs) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
        """Coupling function where land component consistently fails."""
        # Ocean-atmosphere components work
        ocean_vars = {k: v for k, v in variables.items()
                     if k in ['sea_surface_temp', 'air_temp', 'wind_speed', 'heat_flux']}

        if ocean_vars:
            ocean_updated, ocean_residuals = atmospheric_ocean_coupling(ocean_vars, **kwargs)
        else:
            ocean_updated, ocean_residuals = {}, {}

        # Land component always fails
        if any(k in variables for k in ['soil_moisture', 'precipitation', 'evapotranspiration']):
            raise RuntimeError("Land surface model component has failed catastrophically")

        return ocean_updated, ocean_residuals

    initial_variables = {
        'sea_surface_temp': 289.0,
        'air_temp': 287.0,
        'wind_speed': 6.0,
        'heat_flux': 20.0,
        'soil_moisture': 0.35,      # This component will fail
        'precipitation': 3.0,       # This component will fail
        'evapotranspiration': 2.5   # This component will fail
    }

    esm_file = create_earth_system_esm()

    print("Testing partial execution with land component failures...")
    print(f"Initial variables: {list(initial_variables.keys())}")
    print(f"Essential components: {recovery_config.essential_components}")

    result, diagnostic = iterator.iterate_coupling_robust(
        esm_file=esm_file,
        initial_variables=initial_variables,
        coupling_function=failing_land_coupling
    )

    print(f"\nPartial Execution Results:")
    print(f"  Simulation continued: {result.converged or len(result.final_state.variables) > 0}")
    print(f"  Final variables: {list(result.final_state.variables.keys())}")
    print(f"  Essential components preserved: {all(comp in result.final_state.variables for comp in recovery_config.essential_components)}")

    working_components = set(result.final_state.variables.keys())
    failed_components = set(initial_variables.keys()) - working_components
    print(f"  Working components: {working_components}")
    print(f"  Failed components: {failed_components}")

    print(f"\nError Analysis:")
    print(f"  Total errors: {len(diagnostic.errors)}")
    print(f"  Recovery strategies used: {list(diagnostic.recovery_summary.keys())}")

    success = result.converged or (
        len(result.final_state.variables) > 0 and
        all(comp in result.final_state.variables for comp in recovery_config.essential_components)
    )

    if success:
        print("✓ Partial execution successfully maintained essential Earth system components")
    else:
        print("✗ Partial execution failed to maintain essential components")

    print("\n" + "✓ Partial execution resilience demo completed" + "\n")


def main():
    """Run all coupling error handling demonstrations."""
    print("Earth System Model - Coupling Error Handling Demonstrations")
    print("=" * 80)
    print("This demo shows robust coupling error handling for realistic")
    print("Earth system model scenarios with atmosphere-ocean-land interactions.\n")

    try:
        demo_basic_error_recovery()
        demo_fault_tolerant_simulation()
        demo_partial_execution_resilience()

        print("=" * 80)
        print("All demonstrations completed successfully!")
        print("The coupling error handling system is ready for production use.")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())