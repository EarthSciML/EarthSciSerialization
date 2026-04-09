#!/usr/bin/env python3
"""
Test the new simulate function with EsmFile parameter.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import numpy as np

# Import required types and functions
from earthsci_toolkit.types import (
    EsmFile, Metadata, ReactionSystem, Species, Reaction,
    Parameter
)
from earthsci_toolkit.simulation import simulate

def test_esm_file_simulation():
    """Test the new simulate function with EsmFile."""

    print("Testing new simulate function with EsmFile...")

    # Create a simple reaction system: A -> B (first-order decay)
    species = [
        Species(name="A", formula="A", description="Reactant"),
        Species(name="B", formula="B", description="Product")
    ]

    parameters = [
        Parameter(name="k1", value=0.5, units="1/s", description="Rate constant")
    ]

    reactions = [
        Reaction(
            name="decay",
            reactants={"A": 1.0},
            products={"B": 1.0},
            rate_constant="k1"  # Reference to parameter
        )
    ]

    reaction_system = ReactionSystem(
        name="simple_decay",
        species=species,
        parameters=parameters,
        reactions=reactions
    )

    # Create ESM file
    esm_file = EsmFile(
        version="0.1.0",
        metadata=Metadata(
            title="Simple Decay Test",
            description="Test simulation with A -> B decay"
        ),
        reaction_systems=[reaction_system]
    )

    # Simulation parameters
    tspan = (0.0, 5.0)
    parameters_dict = {"k1": 0.1}  # Override parameter value
    initial_conditions = {"A": 1.0, "B": 0.0}

    # Run simulation
    result = simulate(
        file=esm_file,
        tspan=tspan,
        parameters=parameters_dict,
        initial_conditions=initial_conditions,
        method='RK45'
    )

    # Check results
    print(f"Simulation success: {result.success}")
    if result.success:
        print(f"Variable names: {result.vars}")
        print(f"Time points: {len(result.t)}")
        print(f"Final concentrations:")
        for i, var in enumerate(result.vars):
            initial = initial_conditions.get(var, 0.0)
            final = result.y[i, -1]
            print(f"  {var}: {initial:.3f} -> {final:.3f}")

        # Test conservation: A + B should equal initial A
        A_final = result.y[0, -1]  # A is first variable
        B_final = result.y[1, -1]  # B is second variable
        total = A_final + B_final
        expected_total = initial_conditions["A"]

        print(f"Mass conservation check: {total:.6f} (expected: {expected_total})")

        # Test that A decreases and B increases
        A_initial = result.y[0, 0]
        B_initial = result.y[1, 0]

        assert A_final < A_initial, "A should decrease"
        assert B_final > B_initial, "B should increase"
        assert abs(total - expected_total) < 1e-6, "Mass should be conserved"

        print("✅ All tests passed!")

        # Test plotting (if matplotlib is available)
        try:
            import matplotlib.pyplot as plt
            print("Testing plot functionality...")
            fig, ax = result.plot(show=False, save_path="test_simulation_plot.png")
            print("✅ Plot functionality works!")
            plt.close(fig)
        except ImportError:
            print("⚠️  matplotlib not available, skipping plot test")
        except Exception as e:
            print(f"⚠️  Plot test failed: {e}")

    else:
        print(f"❌ Simulation failed: {result.message}")
        return False

    return True

if __name__ == "__main__":
    test_esm_file_simulation()