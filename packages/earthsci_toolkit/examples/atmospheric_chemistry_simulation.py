#!/usr/bin/env python3
"""
Example: Atmospheric Chemistry Simulation

This example demonstrates the Python simulation tier with SciPy integration
for atmospheric chemistry modeling. It implements a simple O3-NOx chemistry
system to showcase the simulation capabilities.
"""

import numpy as np
import matplotlib.pyplot as plt
from earthsci_toolkit.simulation import simulate
from earthsci_toolkit.types import ReactionSystem, Species, Reaction


def create_atmospheric_chemistry_system():
    """
    Create a simple atmospheric chemistry system with O3-NOx reactions.

    Reactions:
    1. NO2 + hv -> NO + O     (photolysis)
    2. O + O2 + M -> O3 + M   (ozone formation, simplified as O -> O3)
    3. NO + O3 -> NO2 + O2    (ozone depletion)
    """
    # Define species
    species = [
        Species(name="NO", formula="NO", description="Nitric oxide"),
        Species(name="NO2", formula="NO2", description="Nitrogen dioxide"),
        Species(name="O", formula="O", description="Atomic oxygen"),
        Species(name="O3", formula="O3", description="Ozone"),
    ]

    # Define reactions with rate constants (simplified)
    reactions = [
        # NO2 photolysis: NO2 -> NO + O (rate = j1 * [NO2])
        Reaction(
            name="NO2_photolysis",
            reactants={"NO2": 1.0},
            products={"NO": 1.0, "O": 1.0},
            rate_constant=0.01  # s^-1 (simplified photolysis rate)
        ),

        # Ozone formation: O -> O3 (simplified from O + O2 + M -> O3 + M)
        Reaction(
            name="ozone_formation",
            reactants={"O": 1.0},
            products={"O3": 1.0},
            rate_constant=1.0  # s^-1 (fast reaction)
        ),

        # Ozone depletion: NO + O3 -> NO2 + O2
        # Using mass action: rate = k * [NO] * [O3]
        # We'll represent this with a more complex rate expression
        Reaction(
            name="ozone_depletion",
            reactants={"NO": 1.0, "O3": 1.0},
            products={"NO2": 1.0},  # O2 is assumed in excess
            rate_constant=0.1  # ppm^-1 s^-1
        ),
    ]

    return ReactionSystem(
        name="atmospheric_chemistry",
        species=species,
        reactions=reactions
    )


def run_atmospheric_simulation():
    """Run the atmospheric chemistry simulation."""
    print("🌍 Atmospheric Chemistry Simulation")
    print("=" * 40)

    # Create the reaction system
    system = create_atmospheric_chemistry_system()

    # Initial conditions (concentrations in ppm)
    initial_conditions = {
        "NO2": 0.05,   # 50 ppb NO2
        "NO": 0.01,    # 10 ppb NO
        "O": 0.0,      # No atomic oxygen initially
        "O3": 0.08,    # 80 ppb O3
    }

    print(f"Initial conditions: {initial_conditions}")

    # Simulation time span (seconds)
    time_span = (0, 3600)  # 1 hour

    print(f"Simulating for {time_span[1]} seconds ({time_span[1]/3600:.1f} hours)")

    # Run simulation
    result = simulate(
        reaction_system=system,
        initial_conditions=initial_conditions,
        time_span=time_span,
        method='LSODA',
        rtol=1e-8,
        atol=1e-10
    )

    # Check if simulation was successful
    if result.success:
        print(f"✅ Simulation completed successfully!")
        print(f"   Function evaluations: {result.nfev}")
        print(f"   Jacobian evaluations: {result.njev}")
        print(f"   LU decompositions: {result.nlu}")
    else:
        print(f"❌ Simulation failed: {result.message}")
        return

    # Extract results
    t_hours = result.t / 3600  # Convert to hours
    species_names = ["NO", "NO2", "O", "O3"]

    # Print final concentrations
    print(f"\nFinal concentrations (after {t_hours[-1]:.1f} hours):")
    for i, species in enumerate(species_names):
        initial = initial_conditions.get(species, 0.0)
        final = result.y[i, -1]
        change = ((final - initial) / initial * 100) if initial > 0 else float('inf')
        print(f"  {species:4s}: {final:.4f} ppm ({change:+.1f}%)")

    # Plot results
    plt.figure(figsize=(12, 8))

    # Time evolution
    plt.subplot(2, 2, 1)
    colors = ['blue', 'red', 'green', 'orange']
    for i, (species, color) in enumerate(zip(species_names, colors)):
        plt.plot(t_hours, result.y[i, :], label=species, color=color, linewidth=2)
    plt.xlabel('Time (hours)')
    plt.ylabel('Concentration (ppm)')
    plt.title('Atmospheric Chemistry Evolution')
    plt.legend()
    plt.grid(True, alpha=0.3)

    # NOx budget (NO + NO2)
    plt.subplot(2, 2, 2)
    nox = result.y[0, :] + result.y[1, :]  # NO + NO2
    plt.plot(t_hours, nox, label='NOx total', color='purple', linewidth=2)
    plt.axhline(y=nox[0], color='purple', linestyle='--', alpha=0.5, label='Initial NOx')
    plt.xlabel('Time (hours)')
    plt.ylabel('NOx Concentration (ppm)')
    plt.title('NOx Conservation')
    plt.legend()
    plt.grid(True, alpha=0.3)

    # Ox budget (O + O3)
    plt.subplot(2, 2, 3)
    ox = result.y[2, :] + result.y[3, :]  # O + O3
    plt.plot(t_hours, ox, label='Ox total', color='brown', linewidth=2)
    plt.axhline(y=ox[0], color='brown', linestyle='--', alpha=0.5, label='Initial Ox')
    plt.xlabel('Time (hours)')
    plt.ylabel('Ox Concentration (ppm)')
    plt.title('Ox Evolution')
    plt.legend()
    plt.grid(True, alpha=0.3)

    # Phase plot: NO vs O3
    plt.subplot(2, 2, 4)
    plt.plot(result.y[0, :], result.y[3, :], color='darkgreen', linewidth=2)
    plt.plot(result.y[0, 0], result.y[3, 0], 'go', markersize=8, label='Start')
    plt.plot(result.y[0, -1], result.y[3, -1], 'ro', markersize=8, label='End')
    plt.xlabel('NO (ppm)')
    plt.ylabel('O3 (ppm)')
    plt.title('NO vs O3 Phase Plot')
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save plot if matplotlib is available
    try:
        plt.savefig('atmospheric_chemistry_simulation.png', dpi=150, bbox_inches='tight')
        print(f"\n📊 Plot saved as 'atmospheric_chemistry_simulation.png'")
    except Exception as e:
        print(f"Could not save plot: {e}")

    plt.show()

    # Verify mass conservation
    print(f"\n🔬 Mass Conservation Check:")
    initial_nox = initial_conditions["NO"] + initial_conditions["NO2"]
    final_nox = result.y[0, -1] + result.y[1, -1]
    nox_error = abs(final_nox - initial_nox) / initial_nox * 100

    print(f"   NOx conservation error: {nox_error:.6f}%")

    if nox_error < 0.01:
        print("   ✅ Excellent mass conservation")
    elif nox_error < 0.1:
        print("   ✅ Good mass conservation")
    else:
        print("   ⚠️  Mass conservation could be improved")


if __name__ == "__main__":
    try:
        run_atmospheric_simulation()
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install required packages: pip install matplotlib")
    except Exception as e:
        print(f"Simulation error: {e}")
        import traceback
        traceback.print_exc()