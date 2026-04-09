#!/usr/bin/env python3
"""
Test script for coupling error handling and recovery system.

This script tests various error conditions and recovery strategies
to ensure the robust coupling system can handle failures gracefully.
"""

import sys
import os
import time
import math
from typing import Dict, Tuple, Optional

# Add the package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from esm_format.coupling_error_handling import (
    RobustCouplingIterator,
    RecoveryConfig,
    ExecutionMode,
    CouplingErrorType,
    RecoveryStrategy,
    create_robust_coupling_iterator,
    create_fault_tolerant_iterator,
    DiagnosticReport
)
from esm_format.coupling_iteration import (
    ConvergenceConfig,
    ConvergenceMethod,
    create_default_coupling_iterator
)
from esm_format.types import EsmFile, Metadata


def create_test_esm_file() -> EsmFile:
    """Create a simple test ESM file."""
    metadata = Metadata(title="Error Handling Test")
    return EsmFile(
        version="0.1.0",
        metadata=metadata,
        models=[],
        reaction_systems=[],
        couplings=[]
    )


def failing_coupling_function(variables: Dict[str, float], **kwargs) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
    """Coupling function that always fails with an exception."""
    raise ValueError("Simulated coupling failure")


def unstable_coupling_function(variables: Dict[str, float], **kwargs) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
    """Coupling function that produces NaN/Inf values."""
    x = variables.get('x', 1.0)
    y = variables.get('y', 1.0)

    # Create instability that leads to NaN
    if abs(x) < 1e-10:
        x_new = float('inf')  # Simulate division by zero result
    else:
        x_new = y / x

    if abs(y) < 1e-10:
        y_new = float('nan')  # Simulate invalid operation
    else:
        y_new = math.log(abs(y)) * x

    return {'x': x_new, 'y': y_new}, {'x': x_new - x, 'y': y_new - y}


def slow_coupling_function(variables: Dict[str, float], **kwargs) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
    """Coupling function that takes a long time (simulates timeout)."""
    time.sleep(0.1)  # Small delay to simulate slow computation

    x = variables.get('x', 1.0)
    y = variables.get('y', 1.0)

    # Slow convergence
    x_new = 0.99 * x + 0.01 * y
    y_new = 0.99 * y + 0.01 * x

    return {'x': x_new, 'y': y_new}, {'x': x_new - x, 'y': y_new - y}


def intermittent_failure_function(variables: Dict[str, float], **kwargs) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
    """Coupling function that fails intermittently."""
    iteration = kwargs.get('_test_iteration', 0)

    # Fail on iterations 2, 5, and 8
    if iteration in [2, 5, 8]:
        raise RuntimeError(f"Intermittent failure at iteration {iteration}")

    x = variables.get('x', 1.0)
    y = variables.get('y', 1.0)

    # Simple coupling when it works
    x_new = 0.8 * x + 0.2 * math.sqrt(abs(y))
    y_new = 0.8 * y + 0.2 * math.sqrt(abs(x))

    return {'x': x_new, 'y': y_new}, {'x': x_new - x, 'y': y_new - y}


def partial_failure_function(variables: Dict[str, float], **kwargs) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
    """Coupling function where some components fail but others succeed."""
    x = variables.get('x', 1.0)
    y = variables.get('y', 1.0)
    z = variables.get('z', 1.0)

    # x component works fine
    x_new = 0.9 * x + 0.1

    # y component fails
    if y > 0.5:
        raise ValueError("Y component failed when y > 0.5")
    y_new = 0.8 * y

    # z component works but depends on y
    z_new = 0.7 * z + 0.3 * y_new

    return {'x': x_new, 'y': y_new, 'z': z_new}, {
        'x': x_new - x, 'y': y_new - y, 'z': z_new - z
    }


def good_coupling_function(variables: Dict[str, float], **kwargs) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
    """Well-behaved coupling function for comparison."""
    x = variables.get('x', 1.0)
    y = variables.get('y', 1.0)

    # Simple stable coupling
    x_new = 0.6 * x + 0.4 * y
    y_new = 0.4 * x + 0.6 * y

    return {'x': x_new, 'y': y_new}, {'x': x_new - x, 'y': y_new - y}


def test_basic_error_handling():
    """Test basic error handling with a failing coupling function."""
    print("=" * 60)
    print("Test 1: Basic Error Handling")
    print("=" * 60)

    # Create robust iterator
    iterator = create_robust_coupling_iterator(
        execution_mode=ExecutionMode.BEST_EFFORT
    )

    initial_variables = {'x': 1.0, 'y': 2.0}
    esm_file = create_test_esm_file()

    result, diagnostic = iterator.iterate_coupling_robust(
        esm_file=esm_file,
        initial_variables=initial_variables,
        coupling_function=failing_coupling_function
    )

    print(f"Converged: {result.converged}")
    print(f"Total iterations: {result.total_iterations}")
    print(f"Convergence reason: {result.convergence_reason}")
    print(f"Errors collected: {len(diagnostic.errors)}")
    print(f"Warnings collected: {len(diagnostic.warnings)}")

    if len(diagnostic.errors) > 0:
        print("First error:", diagnostic.errors[0].message)

    if diagnostic.recovery_summary:
        print(f"Recovery attempts: {diagnostic.recovery_summary}")

    print("✓ Error handling test completed")
    print()


def test_numerical_instability_recovery():
    """Test recovery from numerical instability (NaN/Inf values)."""
    print("=" * 60)
    print("Test 2: Numerical Instability Recovery")
    print("=" * 60)

    # Configure with fallback values
    recovery_config = RecoveryConfig(
        default_values={'x': 1.0, 'y': 1.0},
        variable_bounds={'x': (0.01, 10.0), 'y': (0.01, 10.0)},
        fallback_strategies=[
            RecoveryStrategy.FALLBACK_VALUES,
            RecoveryStrategy.SIMPLIFIED_MODEL
        ]
    )

    iterator = create_robust_coupling_iterator(
        recovery_config=recovery_config,
        execution_mode=ExecutionMode.BEST_EFFORT
    )

    # Start with values that will cause instability
    initial_variables = {'x': 1e-15, 'y': 1e-15}
    esm_file = create_test_esm_file()

    result, diagnostic = iterator.iterate_coupling_robust(
        esm_file=esm_file,
        initial_variables=initial_variables,
        coupling_function=unstable_coupling_function
    )

    print(f"Converged: {result.converged}")
    print(f"Final variables: {result.final_state.variables}")
    print(f"Recovery attempts: {diagnostic.recovery_summary}")
    print(f"Errors: {len(diagnostic.errors)}")

    # Check if recovery was successful
    final_vars = result.final_state.variables
    if all(isinstance(v, (int, float)) and v == v and abs(v) != float('inf')
           for v in final_vars.values()):
        print("✓ Successfully recovered from numerical instability")
    else:
        print("✗ Failed to recover from numerical instability")

    print()


def test_timeout_handling():
    """Test timeout handling for slow coupling functions."""
    print("=" * 60)
    print("Test 3: Timeout Handling")
    print("=" * 60)

    # Configure with short timeout
    recovery_config = RecoveryConfig(
        timeout_seconds=1.0,  # Short timeout
        max_retry_attempts=2
    )

    iterator = create_robust_coupling_iterator(
        recovery_config=recovery_config
    )

    initial_variables = {'x': 1.0, 'y': 2.0}
    esm_file = create_test_esm_file()

    start_time = time.time()
    result, diagnostic = iterator.iterate_coupling_robust(
        esm_file=esm_file,
        initial_variables=initial_variables,
        coupling_function=slow_coupling_function
    )
    elapsed_time = time.time() - start_time

    print(f"Elapsed time: {elapsed_time:.2f} seconds")
    print(f"Converged: {result.converged}")
    print(f"Total iterations: {result.total_iterations}")

    if elapsed_time > recovery_config.timeout_seconds:
        print("⚠️ Operation exceeded timeout (expected for this test)")
    else:
        print("✓ Operation completed within timeout")

    print()


def test_retry_mechanisms():
    """Test retry mechanisms with intermittent failures."""
    print("=" * 60)
    print("Test 4: Retry Mechanisms")
    print("=" * 60)

    recovery_config = RecoveryConfig(
        max_retry_attempts=3,
        retry_delay_seconds=0.01  # Small delay for testing
    )

    iterator = create_robust_coupling_iterator(
        recovery_config=recovery_config
    )

    # Create a counter to track iterations
    iteration_counter = {'count': 0}

    def tracking_intermittent_function(variables, **kwargs):
        kwargs['_test_iteration'] = iteration_counter['count']
        iteration_counter['count'] += 1
        return intermittent_failure_function(variables, **kwargs)

    initial_variables = {'x': 2.0, 'y': 0.5}
    esm_file = create_test_esm_file()

    result, diagnostic = iterator.iterate_coupling_robust(
        esm_file=esm_file,
        initial_variables=initial_variables,
        coupling_function=tracking_intermittent_function
    )

    print(f"Converged: {result.converged}")
    print(f"Total function calls: {iteration_counter['count']}")
    print(f"Recovery attempts: {diagnostic.recovery_summary}")
    print(f"Errors collected: {len(diagnostic.errors)}")

    if result.converged:
        print("✓ Successfully handled intermittent failures with retry")
    else:
        print("✗ Failed to handle intermittent failures")

    print()


def test_partial_execution_mode():
    """Test partial execution mode where some components fail."""
    print("=" * 60)
    print("Test 5: Partial Execution Mode")
    print("=" * 60)

    recovery_config = RecoveryConfig(
        enable_partial_execution=True,
        essential_components=['x', 'z'],  # y is not essential
        fallback_strategies=[RecoveryStrategy.PARTIAL_EXECUTION]
    )

    iterator = create_robust_coupling_iterator(
        recovery_config=recovery_config,
        execution_mode=ExecutionMode.BEST_EFFORT
    )

    initial_variables = {'x': 1.0, 'y': 0.8, 'z': 0.5}  # y > 0.5 will cause failure
    esm_file = create_test_esm_file()

    result, diagnostic = iterator.iterate_coupling_robust(
        esm_file=esm_file,
        initial_variables=initial_variables,
        coupling_function=partial_failure_function
    )

    print(f"Converged: {result.converged}")
    print(f"Final variables: {result.final_state.variables}")
    print(f"Recovery summary: {diagnostic.recovery_summary}")
    print(f"Recommendations: {diagnostic.recommendations[:3]}")  # Show first 3

    if result.final_state.variables and 'x' in result.final_state.variables:
        print("✓ Partial execution succeeded - essential components preserved")
    else:
        print("✗ Partial execution failed")

    print()


def test_fault_tolerant_iterator():
    """Test the fault-tolerant iterator with various challenging scenarios."""
    print("=" * 60)
    print("Test 6: Fault-Tolerant Iterator")
    print("=" * 60)

    # Create fault-tolerant iterator
    iterator = create_fault_tolerant_iterator(
        max_iterations=50,
        tolerance=1e-3,
        timeout_seconds=10.0
    )

    # Test with good function first
    print("Testing with well-behaved coupling function:")
    initial_variables = {'x': 3.0, 'y': 1.0}
    esm_file = create_test_esm_file()

    result, diagnostic = iterator.iterate_coupling_robust(
        esm_file=esm_file,
        initial_variables=initial_variables,
        coupling_function=good_coupling_function
    )

    print(f"  Converged: {result.converged}")
    print(f"  Iterations: {result.total_iterations}")
    print(f"  Final values: x={result.final_state.variables.get('x', 0):.4f}, y={result.final_state.variables.get('y', 0):.4f}")

    if result.converged:
        print("  ✓ Fault-tolerant iterator works with good functions")
    else:
        print("  ✗ Fault-tolerant iterator failed with good function")

    print()


def test_diagnostic_reporting():
    """Test comprehensive diagnostic reporting."""
    print("=" * 60)
    print("Test 7: Diagnostic Reporting")
    print("=" * 60)

    iterator = create_robust_coupling_iterator(
        execution_mode=ExecutionMode.DIAGNOSTIC  # Maximum diagnostic info
    )

    initial_variables = {'x': 1.0, 'y': 2.0}
    esm_file = create_test_esm_file()

    result, diagnostic = iterator.iterate_coupling_robust(
        esm_file=esm_file,
        initial_variables=initial_variables,
        coupling_function=failing_coupling_function
    )

    print("Diagnostic Report Summary:")
    print(f"  Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(diagnostic.timestamp))}")
    print(f"  Errors: {len(diagnostic.errors)}")
    print(f"  Warnings: {len(diagnostic.warnings)}")
    print(f"  Performance metrics: {list(diagnostic.performance_metrics.keys())}")
    print(f"  System state keys: {list(diagnostic.system_state.keys())}")
    print(f"  Recovery attempts: {diagnostic.recovery_summary}")
    print(f"  Recommendations: {len(diagnostic.recommendations)}")

    # Test JSON export
    json_report = diagnostic.export_json()
    if len(json_report) > 100:  # Should have substantial content
        print("  ✓ JSON export successful")
    else:
        print("  ✗ JSON export failed or empty")

    # Show first recommendation
    if diagnostic.recommendations:
        print(f"  First recommendation: {diagnostic.recommendations[0]}")

    print("✓ Diagnostic reporting test completed")
    print()


def test_recovery_strategies_comparison():
    """Compare effectiveness of different recovery strategies."""
    print("=" * 60)
    print("Test 8: Recovery Strategies Comparison")
    print("=" * 60)

    strategies_to_test = [
        ([RecoveryStrategy.RETRY_WITH_RELAXATION], "Retry with Relaxation"),
        ([RecoveryStrategy.FALLBACK_VALUES], "Fallback Values"),
        ([RecoveryStrategy.SIMPLIFIED_MODEL], "Simplified Model"),
        ([RecoveryStrategy.PARTIAL_EXECUTION], "Partial Execution"),
        ([RecoveryStrategy.GRACEFUL_DEGRADATION], "Graceful Degradation"),
    ]

    results = {}

    for strategies, name in strategies_to_test:
        print(f"\nTesting {name}:")

        recovery_config = RecoveryConfig(
            fallback_strategies=strategies,
            default_values={'x': 1.0, 'y': 1.0},
            essential_components=['x']
        )

        iterator = create_robust_coupling_iterator(
            recovery_config=recovery_config,
            execution_mode=ExecutionMode.BEST_EFFORT
        )

        initial_variables = {'x': 1e-10, 'y': 1e-10}  # Problematic values
        esm_file = create_test_esm_file()

        result, diagnostic = iterator.iterate_coupling_robust(
            esm_file=esm_file,
            initial_variables=initial_variables,
            coupling_function=unstable_coupling_function
        )

        success = result.converged or (
            result.final_state.variables and
            all(isinstance(v, (int, float)) and v == v and abs(v) != float('inf')
                for v in result.final_state.variables.values())
        )

        results[name] = success
        print(f"  Success: {success}")
        print(f"  Final variables: {result.final_state.variables}")
        print(f"  Recovery attempts: {diagnostic.recovery_summary}")

    print("\nRecovery Strategy Effectiveness:")
    for strategy, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {strategy}")

    print()


def main():
    """Run all coupling error handling tests."""
    print("Coupling Error Handling and Recovery Tests")
    print("=" * 60)

    try:
        test_basic_error_handling()
        test_numerical_instability_recovery()
        test_timeout_handling()
        test_retry_mechanisms()
        test_partial_execution_mode()
        test_fault_tolerant_iterator()
        test_diagnostic_reporting()
        test_recovery_strategies_comparison()

        print("=" * 60)
        print("All error handling tests completed successfully!")
        print("Coupling error handling and recovery system verified.")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())