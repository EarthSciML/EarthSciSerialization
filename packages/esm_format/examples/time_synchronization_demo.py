#!/usr/bin/env python3
"""
Time Synchronization Demo

This example demonstrates the time synchronization algorithms for coupled
ESM components with different time steps, showing interpolation, extrapolation,
and time alignment strategies.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from esm_format.time_synchronization import (
    TimeSynchronizer,
    TimeStep,
    TimeInterpolationMethod,
    TimeAlignmentStrategy,
    synchronize_coupled_system,
    create_subcycling_synchronizer
)
from esm_format.types import CouplingEntry, CouplingType


def demo_basic_synchronization():
    """Demonstrate basic time synchronization between two components."""
    print("=== Basic Time Synchronization Demo ===")

    # Create synchronizer
    sync = TimeSynchronizer()
    sync.set_alignment_strategy(TimeAlignmentStrategy.SYNCHRONOUS)

    # Register components with different time steps
    sync.register_component("atmosphere", TimeStep(1.0, "seconds"))
    sync.register_component("ocean", TimeStep(3.0, "seconds"))

    # Add some initial data
    sync.components["atmosphere"].add_data_point({"temperature": 273.0, "pressure": 1013.25})
    sync.components["ocean"].add_data_point({"temperature": 283.0, "salinity": 35.0})

    print(f"Initial atmosphere time: {sync.components['atmosphere'].current_time}s")
    print(f"Initial ocean time: {sync.components['ocean'].current_time}s")

    # Simulate several time steps
    for step in range(5):
        sync_time = sync.advance_to_sync_time()
        print(f"\nStep {step + 1}: Synchronized at t={sync_time}s")

        # Add new data at current times
        for name, comp in sync.components.items():
            if abs(comp.current_time - sync_time) < 1e-9:  # Component updated
                if name == "atmosphere":
                    # Simulate cooling
                    temp = 273.0 - comp.current_time * 0.1
                    comp.add_data_point({"temperature": temp, "pressure": 1013.25})
                elif name == "ocean":
                    # Simulate warming
                    temp = 283.0 + comp.current_time * 0.05
                    comp.add_data_point({"temperature": temp, "salinity": 35.0})

                print(f"  {name}: t={comp.current_time}s, next_update={comp.next_update_time}s")


def demo_interpolation():
    """Demonstrate time interpolation capabilities."""
    print("\n\n=== Time Interpolation Demo ===")

    sync = TimeSynchronizer()
    sync.register_component("fast_physics", TimeStep(0.5, "seconds"))

    comp = sync.components["fast_physics"]

    # Add data at regular intervals
    times_and_temps = [(0.0, 273.0), (1.0, 275.0), (2.0, 277.0), (3.0, 279.0)]

    for time, temp in times_and_temps:
        comp.current_time = time
        comp.add_data_point({"temperature": temp})

    print("Data points:")
    for point in comp.history.points:
        print(f"  t={point.time}s: temperature={point.data['temperature']}K")

    # Test interpolation at various times
    test_times = [0.5, 1.5, 2.7]

    print("\nLinear interpolation:")
    for test_time in test_times:
        result = sync.interpolate_data(
            "fast_physics",
            test_time,
            ["temperature"],
            TimeInterpolationMethod.LINEAR
        )
        print(f"  t={test_time}s: temperature={result['temperature']:.1f}K")

    print("\nNearest neighbor interpolation:")
    for test_time in test_times:
        result = sync.interpolate_data(
            "fast_physics",
            test_time,
            ["temperature"],
            TimeInterpolationMethod.NEAREST
        )
        print(f"  t={test_time}s: temperature={result['temperature']:.1f}K")

    # Test extrapolation
    print("\nExtrapolation beyond data range:")
    extrapolation_times = [4.0, 5.0]
    for test_time in extrapolation_times:
        result = sync.interpolate_data(
            "fast_physics",
            test_time,
            ["temperature"],
            TimeInterpolationMethod.LINEAR
        )
        print(f"  t={test_time}s: temperature={result['temperature']:.1f}K")


def demo_subcycling():
    """Demonstrate subcycling between fast and slow components."""
    print("\n\n=== Subcycling Demo ===")

    # Create fast-slow subcycling setup
    fast_comp = ("dynamics", TimeStep(0.1, "seconds"))
    slow_comp = ("physics", TimeStep(1.0, "seconds"))
    coupling_vars = (["velocity"], ["wind_speed"])

    sync = create_subcycling_synchronizer(fast_comp, slow_comp, coupling_vars)

    print(f"Fast component ({fast_comp[0]}): dt = {fast_comp[1].value} {fast_comp[1].units}")
    print(f"Slow component ({slow_comp[0]}): dt = {slow_comp[1].value} {slow_comp[1].units}")
    print(f"Alignment strategy: {sync.alignment_strategy.value}")
    print(f"Number of couplings: {len(sync.couplings)}")

    # Show first few synchronization steps
    print("\nSynchronization schedule:")
    for step in range(12):
        next_sync = sync.get_next_sync_time()
        if next_sync > 1.2:  # Stop after a bit
            break

        sync.advance_to_sync_time()

        # Check which components updated
        updated_comps = []
        for name, comp in sync.components.items():
            if abs(comp.current_time - next_sync) < 1e-9:
                updated_comps.append(name)

        print(f"  Step {step + 1}: t={next_sync:.1f}s, updated: {', '.join(updated_comps)}")


def demo_coupled_system():
    """Demonstrate full coupled system simulation."""
    print("\n\n=== Coupled System Demo ===")

    # Define components with initial conditions
    components = {
        "atmosphere": (TimeStep(2.0, "seconds"), {"temperature": 288.0, "pressure": 1013.0}),
        "surface": (TimeStep(1.0, "seconds"), {"temperature": 285.0, "heat_flux": 100.0}),
        "subsurface": (TimeStep(5.0, "seconds"), {"temperature": 283.0, "moisture": 0.3})
    }

    # Define couplings
    couplings = [
        CouplingEntry(
            source_model="atmosphere",
            target_model="surface",
            source_variables=["temperature"],
            target_variables=["air_temperature"],
            coupling_type=CouplingType.INTERPOLATED
        ),
        CouplingEntry(
            source_model="surface",
            target_model="subsurface",
            source_variables=["heat_flux"],
            target_variables=["surface_heat_flux"],
            coupling_type=CouplingType.DIRECT
        )
    ]

    print("Components:")
    for name, (timestep, initial_data) in components.items():
        print(f"  {name}: dt={timestep.value}{timestep.units}, vars={list(initial_data.keys())}")

    print("\nCouplings:")
    for i, coupling in enumerate(couplings):
        print(f"  {i+1}: {coupling.source_model} -> {coupling.target_model} "
              f"({coupling.coupling_type.value})")

    # Run simulation
    print(f"\nRunning 10-second simulation...")

    result = synchronize_coupled_system(
        components=components,
        couplings=couplings,
        simulation_duration=10.0,
        alignment_strategy=TimeAlignmentStrategy.SYNCHRONOUS,
        interpolation_method=TimeInterpolationMethod.LINEAR
    )

    print(f"Simulation completed:")
    print(f"  Final time: {result['final_time']:.1f}s")
    print(f"  Total steps: {result['simulation_steps']}")
    print(f"  Components: {result['num_components']}")
    print(f"  Couplings: {result['num_couplings']}")

    print(f"\nFinal component states:")
    for name, state in result['components'].items():
        print(f"  {name}: t={state['current_time']:.1f}s, "
              f"history_length={state['history_length']}")


if __name__ == "__main__":
    print("Time Synchronization Demo for Coupled ESM Components")
    print("=" * 60)

    try:
        demo_basic_synchronization()
        demo_interpolation()
        demo_subcycling()
        demo_coupled_system()

        print(f"\n\n{'='*60}")
        print("Demo completed successfully!")

    except Exception as e:
        print(f"Error during demo: {e}")
        import traceback
        traceback.print_exc()