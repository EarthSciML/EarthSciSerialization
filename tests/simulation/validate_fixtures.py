#!/usr/bin/env python3
"""
Validation script for end-to-end simulation test fixtures.

This script validates that all created ESM files parse correctly and contain
the required elements for comprehensive simulation testing.
"""
import json
import os
import sys
from pathlib import Path

# Add the esm_format package to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages/esm_format/src"))

try:
    from esm_format.parse import load
    from esm_format.validation import validate
except ImportError as e:
    print(f"Error: Could not import ESM format modules: {e}")
    print("Make sure the Python package is installed correctly.")
    sys.exit(1)


def validate_fixture(esm_file, reference_file=None):
    """Validate an ESM fixture file and its optional reference solution."""
    print(f"\n=== Validating {esm_file} ===")

    try:
        # Load and parse the ESM file
        esm_data = load(esm_file)
        print("✓ ESM file parsed successfully")

        # Check format version
        if esm_data.get('esm') != '0.1.0':
            print(f"⚠ Warning: Expected ESM version 0.1.0, got {esm_data.get('esm')}")

        # Check metadata
        metadata = esm_data.get('metadata', {})
        required_metadata = ['name', 'description', 'authors', 'created']
        for field in required_metadata:
            if field not in metadata:
                print(f"⚠ Warning: Missing metadata field: {field}")
            else:
                print(f"✓ Metadata {field}: {metadata[field]}")

        # Check domain
        domain = esm_data.get('domain', {})
        if 'temporal' not in domain:
            print("⚠ Warning: No temporal domain specified")
        else:
            temporal = domain['temporal']
            print(f"✓ Temporal domain: {temporal.get('start', 'N/A')} to {temporal.get('end', 'N/A')}")

        # Check solver configuration
        solver = esm_data.get('solver', {})
        if not solver:
            print("⚠ Warning: No solver configuration specified")
        else:
            print(f"✓ Solver strategy: {solver.get('strategy', 'N/A')}")

        # Count systems and components
        models = esm_data.get('models', {})
        reactions = esm_data.get('reaction_systems', {})
        coupling = esm_data.get('coupling', [])
        events_found = False

        for model_name, model_data in models.items():
            variables = model_data.get('variables', {})
            equations = model_data.get('equations', [])
            events = model_data.get('events', [])
            print(f"✓ Model '{model_name}': {len(variables)} variables, {len(equations)} equations, {len(events)} events")
            if events:
                events_found = True

        for reaction_name, reaction_data in reactions.items():
            species = reaction_data.get('species', {})
            reactions_list = reaction_data.get('reactions', [])
            print(f"✓ Reaction system '{reaction_name}': {len(species)} species, {len(reactions_list)} reactions")

        if coupling:
            print(f"✓ Coupling: {len(coupling)} coupling relationships")

        if events_found:
            print("✓ Events: Continuous/discrete event handling present")

        # Validate reference solution if provided
        if reference_file and os.path.exists(reference_file):
            print(f"\n--- Validating reference solution {reference_file} ---")
            try:
                with open(reference_file, 'r') as f:
                    ref_data = json.load(f)

                sim_results = ref_data.get('simulation_results', {})
                if 'metadata' in sim_results:
                    print("✓ Reference solution metadata present")
                if 'time_series' in sim_results:
                    print("✓ Reference solution time series present")
                if 'validation_metrics' in sim_results:
                    print("✓ Reference solution validation metrics present")

                # Check numerical accuracy requirements
                if 'numerical_accuracy_requirements' in ref_data:
                    accuracy = ref_data['numerical_accuracy_requirements']
                    print(f"✓ Accuracy requirements: rtol={accuracy.get('relative_tolerance', 'N/A')}")

            except Exception as e:
                print(f"⚠ Warning: Could not validate reference solution: {e}")

        return True

    except Exception as e:
        print(f"✗ Error validating {esm_file}: {e}")
        return False


def main():
    """Main validation function."""
    print("ESM Simulation Test Fixtures Validation")
    print("=" * 50)

    # Define test fixtures
    fixtures_dir = Path(__file__).parent
    reference_dir = fixtures_dir / "reference_solutions"

    test_fixtures = [
        ("simple_ode.esm", "simple_ode_solution.json"),
        ("coupled_oscillators.esm", "coupled_oscillators_solution.json"),
        ("autocatalytic_reaction.esm", "autocatalytic_reaction_solution.json"),
        ("bouncing_ball.esm", "bouncing_ball_solution.json"),
        ("periodic_dosing.esm", "periodic_dosing_solution.json"),
        ("stiff_ode_system.esm", None),
        ("spatial_diffusion.esm", None),
        ("performance_benchmarks.esm", None),
    ]

    success_count = 0
    total_count = len(test_fixtures)

    for esm_file, ref_file in test_fixtures:
        esm_path = fixtures_dir / esm_file
        ref_path = reference_dir / ref_file if ref_file else None

        if esm_path.exists():
            if validate_fixture(str(esm_path), str(ref_path) if ref_path else None):
                success_count += 1
        else:
            print(f"✗ Missing fixture: {esm_file}")

    print("\n" + "=" * 50)
    print(f"Validation Summary: {success_count}/{total_count} fixtures validated successfully")

    if success_count == total_count:
        print("🎉 All simulation test fixtures are valid!")
        return 0
    else:
        print(f"⚠ {total_count - success_count} fixtures failed validation")
        return 1


if __name__ == "__main__":
    sys.exit(main())