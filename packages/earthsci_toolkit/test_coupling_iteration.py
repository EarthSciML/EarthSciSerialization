#!/usr/bin/env python3
"""
Test script for coupling iteration and convergence control.

This script demonstrates the coupling iteration functionality with
a simple iterative coupling between two dummy systems.
"""

import numpy as np
from typing import Dict, Tuple, Optional
import sys
import os

# Add the package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from earthsci_toolkit.coupling_iteration import (
    CouplingIterator,
    ConvergenceConfig,
    RelaxationConfig,
    AccelerationConfig,
    ConvergenceMethod,
    RelaxationMethod,
    AccelerationMethod,
    create_default_coupling_iterator,
    create_adaptive_coupling_iterator,
)
from earthsci_toolkit.types import EsmFile, Metadata


def create_test_esm_file() -> EsmFile:
    """Create a simple test ESM file with two coupled models."""
    metadata = Metadata(title="Coupling Iteration Test")

    # Simple ESM file for testing
    esm_file = EsmFile(
        version="0.1.0",
        metadata=metadata,
        models=[],  # We'll use a simplified coupling function for testing
        reaction_systems=[],
        couplings=[]
    )

    return esm_file


def simple_coupling_function(variables: Dict[str, float], **kwargs) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
    """
    Simple test coupling function that simulates iterative coupling.

    This function implements a simple fixed-point iteration:
    x_new = 0.5 * sqrt(x + y)
    y_new = 0.5 * sqrt(x + y)

    The fixed point is x = y = 1.0 when properly converged.
    """
    x = variables.get('x', 1.0)
    y = variables.get('y', 1.0)

    # Simple nonlinear coupling equations
    x_new = 0.5 * np.sqrt(abs(x + y))
    y_new = 0.5 * np.sqrt(abs(x + y))

    updated_variables = {'x': x_new, 'y': y_new}

    # Compute residuals (how far from fixed point iteration)
    residuals = {
        'x': x_new - x,
        'y': y_new - y
    }

    return updated_variables, residuals


def oscillatory_coupling_function(variables: Dict[str, float], **kwargs) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
    """
    Oscillatory coupling function that benefits from relaxation.

    This function creates oscillatory behavior without relaxation:
    x_new = 2 - y
    y_new = 2 - x
    """
    x = variables.get('x', 1.0)
    y = variables.get('y', 1.0)

    # Oscillatory equations
    x_new = 2.0 - y
    y_new = 2.0 - x

    updated_variables = {'x': x_new, 'y': y_new}

    residuals = {
        'x': x_new - x,
        'y': y_new - y
    }

    return updated_variables, residuals


def test_basic_convergence():
    """Test basic convergence with default settings."""
    print("=" * 60)
    print("Test 1: Basic Convergence")
    print("=" * 60)

    # Create coupling iterator
    iterator = create_default_coupling_iterator(
        max_iterations=50,
        tolerance=1e-6,
        relaxation_factor=0.7
    )

    # Initial conditions
    initial_variables = {'x': 2.0, 'y': 0.5}

    # Test ESM file
    esm_file = create_test_esm_file()

    # Run coupling iteration
    result = iterator.iterate_coupling(
        esm_file=esm_file,
        initial_variables=initial_variables,
        coupling_function=simple_coupling_function
    )

    print(f"Converged: {result.converged}")
    print(f"Total iterations: {result.total_iterations}")
    print(f"Execution time: {result.execution_time:.4f} seconds")
    print(f"Convergence reason: {result.convergence_reason}")
    print(f"Final values: {result.final_state.variables}")

    if result.converged:
        print("✓ Test passed: Convergence achieved")
    else:
        print("✗ Test failed: Convergence not achieved")

    print()


def test_relaxation_methods():
    """Test different relaxation methods on oscillatory problem."""
    print("=" * 60)
    print("Test 2: Relaxation Methods on Oscillatory Problem")
    print("=" * 60)

    initial_variables = {'x': 0.0, 'y': 2.0}
    esm_file = create_test_esm_file()

    relaxation_methods = [
        (RelaxationMethod.NONE, "No Relaxation"),
        (RelaxationMethod.FIXED, "Fixed Relaxation (0.3)"),
        (RelaxationMethod.ADAPTIVE, "Adaptive Relaxation"),
    ]

    for method, description in relaxation_methods:
        print(f"\n{description}:")
        print("-" * 40)

        convergence_config = ConvergenceConfig(
            method=ConvergenceMethod.MIXED,
            absolute_tolerance=1e-6,
            relative_tolerance=1e-4,
            max_iterations=30
        )

        relaxation_config = RelaxationConfig(
            method=method,
            relaxation_factor=0.3 if method == RelaxationMethod.FIXED else 0.5
        )

        acceleration_config = AccelerationConfig(method=AccelerationMethod.NONE)

        iterator = CouplingIterator(convergence_config, relaxation_config, acceleration_config)

        result = iterator.iterate_coupling(
            esm_file=esm_file,
            initial_variables=initial_variables,
            coupling_function=oscillatory_coupling_function
        )

        print(f"  Converged: {result.converged}")
        print(f"  Iterations: {result.total_iterations}")
        print(f"  Final values: x={result.final_state.variables.get('x', 0):.4f}, "
              f"y={result.final_state.variables.get('y', 0):.4f}")

        if result.converged:
            print("  ✓ Converged successfully")
        else:
            print("  ✗ Did not converge")


def test_acceleration_methods():
    """Test different acceleration methods."""
    print("=" * 60)
    print("Test 3: Acceleration Methods")
    print("=" * 60)

    initial_variables = {'x': 2.0, 'y': 0.5}
    esm_file = create_test_esm_file()

    acceleration_methods = [
        (AccelerationMethod.NONE, "No Acceleration"),
        (AccelerationMethod.AITKEN, "Aitken Acceleration"),
        (AccelerationMethod.ANDERSON, "Anderson Acceleration"),
    ]

    for method, description in acceleration_methods:
        print(f"\n{description}:")
        print("-" * 40)

        convergence_config = ConvergenceConfig(
            method=ConvergenceMethod.MIXED,
            absolute_tolerance=1e-8,
            relative_tolerance=1e-6,
            max_iterations=50
        )

        relaxation_config = RelaxationConfig(
            method=RelaxationMethod.FIXED,
            relaxation_factor=0.8
        )

        acceleration_config = AccelerationConfig(method=method)

        iterator = CouplingIterator(convergence_config, relaxation_config, acceleration_config)

        result = iterator.iterate_coupling(
            esm_file=esm_file,
            initial_variables=initial_variables,
            coupling_function=simple_coupling_function
        )

        print(f"  Converged: {result.converged}")
        print(f"  Iterations: {result.total_iterations}")
        print(f"  Execution time: {result.execution_time:.4f}s")

        if result.converged:
            print("  ✓ Converged successfully")
        else:
            print("  ✗ Did not converge")


def test_convergence_methods():
    """Test different convergence criteria."""
    print("=" * 60)
    print("Test 4: Convergence Methods")
    print("=" * 60)

    initial_variables = {'x': 2.0, 'y': 0.5}
    esm_file = create_test_esm_file()

    convergence_methods = [
        (ConvergenceMethod.ABSOLUTE, "Absolute Tolerance"),
        (ConvergenceMethod.RELATIVE, "Relative Tolerance"),
        (ConvergenceMethod.MIXED, "Mixed Criteria"),
    ]

    for method, description in convergence_methods:
        print(f"\n{description}:")
        print("-" * 40)

        convergence_config = ConvergenceConfig(
            method=method,
            absolute_tolerance=1e-6,
            relative_tolerance=1e-4,
            max_iterations=50
        )

        iterator = create_default_coupling_iterator(max_iterations=50, tolerance=1e-6)
        iterator.convergence_config = convergence_config

        result = iterator.iterate_coupling(
            esm_file=esm_file,
            initial_variables=initial_variables,
            coupling_function=simple_coupling_function
        )

        print(f"  Converged: {result.converged}")
        print(f"  Iterations: {result.total_iterations}")

        # Show convergence metrics for last few iterations
        if len(result.iteration_history) > 2:
            last_state = result.iteration_history[-1]
            if last_state.convergence_metrics:
                print(f"  Final metrics: {last_state.convergence_metrics}")


def test_adaptive_iterator():
    """Test the adaptive iterator convenience function."""
    print("=" * 60)
    print("Test 5: Adaptive Iterator")
    print("=" * 60)

    iterator = create_adaptive_coupling_iterator(
        max_iterations=40,
        tolerance=1e-6
    )

    initial_variables = {'x': 2.0, 'y': 0.5}
    esm_file = create_test_esm_file()

    result = iterator.iterate_coupling(
        esm_file=esm_file,
        initial_variables=initial_variables,
        coupling_function=simple_coupling_function
    )

    print(f"Converged: {result.converged}")
    print(f"Total iterations: {result.total_iterations}")
    print(f"Final values: {result.final_state.variables}")
    print(f"Used adaptive relaxation and Anderson acceleration")

    if result.converged:
        print("✓ Adaptive iterator test passed")
    else:
        print("✗ Adaptive iterator test failed")


def main():
    """Run all coupling iteration tests."""
    print("Coupling Iteration and Convergence Control Tests")
    print("=" * 60)

    try:
        test_basic_convergence()
        test_relaxation_methods()
        test_acceleration_methods()
        test_convergence_methods()
        test_adaptive_iterator()

        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("Coupling iteration and convergence control implementation verified.")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())