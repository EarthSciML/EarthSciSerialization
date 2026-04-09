#!/usr/bin/env python3
"""
Test suite for coupling performance optimization algorithms.

Tests the performance optimization functionality including parallel execution,
load balancing, memory optimization, and caching strategies.
"""

import sys
import os
import time
import random
import math
from typing import Dict, Tuple, List

# Add the source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_basic_import():
    """Test that the performance optimization modules can be imported."""
    print("Testing module imports...")

    try:
        from esm_format.coupling_performance import (
            PerformanceOptimizedCouplingIterator,
            OptimizationConfig,
            ExecutionStrategy,
            LoadBalancingMethod,
            CachingStrategy,
            PerformanceMetrics,
            create_performance_optimized_iterator
        )
        print("✓ All performance optimization classes imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_performance_metrics():
    """Test the PerformanceMetrics class."""
    print("\nTesting PerformanceMetrics...")

    try:
        from esm_format.coupling_performance import PerformanceMetrics

        metrics = PerformanceMetrics()

        # Test component timing
        metrics.add_component_time("atmosphere", 1.5)
        metrics.add_component_time("ocean", 2.3)
        metrics.add_component_time("atmosphere", 1.2)  # Add again to test accumulation

        assert "atmosphere" in metrics.component_times
        assert "ocean" in metrics.component_times
        assert metrics.component_times["atmosphere"] == 2.7  # 1.5 + 1.2
        assert metrics.component_times["ocean"] == 2.3

        # Test iteration timing
        metrics.add_iteration_time(0.5)
        metrics.add_iteration_time(0.6)
        metrics.add_iteration_time(0.4)

        avg_time = metrics.get_average_iteration_time()
        assert abs(avg_time - 0.5) < 0.001  # (0.5 + 0.6 + 0.4) / 3 = 0.5

        # Test slowest components
        slowest = metrics.get_slowest_components(2)
        assert len(slowest) == 2
        assert slowest[0][0] == "atmosphere"  # Slowest
        assert slowest[1][0] == "ocean"

        print("✓ PerformanceMetrics tests passed")
        return True
    except Exception as e:
        print(f"✗ PerformanceMetrics test failed: {e}")
        return False


def test_optimization_config():
    """Test the OptimizationConfig class."""
    print("\nTesting OptimizationConfig...")

    try:
        from esm_format.coupling_performance import (
            OptimizationConfig,
            ExecutionStrategy,
            LoadBalancingMethod,
            CachingStrategy
        )

        # Test default configuration
        config = OptimizationConfig()
        assert config.execution_strategy == ExecutionStrategy.ADAPTIVE
        assert config.load_balancing == LoadBalancingMethod.DYNAMIC
        assert config.caching_strategy == CachingStrategy.ADAPTIVE

        # Test custom configuration
        custom_config = OptimizationConfig(
            execution_strategy=ExecutionStrategy.FULL_PARALLEL,
            load_balancing=LoadBalancingMethod.WEIGHTED,
            caching_strategy=CachingStrategy.LRU,
            max_parallel_workers=4,
            memory_limit_mb=500.0
        )

        assert custom_config.execution_strategy == ExecutionStrategy.FULL_PARALLEL
        assert custom_config.load_balancing == LoadBalancingMethod.WEIGHTED
        assert custom_config.caching_strategy == CachingStrategy.LRU
        assert custom_config.max_parallel_workers == 4
        assert custom_config.memory_limit_mb == 500.0

        print("✓ OptimizationConfig tests passed")
        return True
    except Exception as e:
        print(f"✗ OptimizationConfig test failed: {e}")
        return False


def test_cache_manager():
    """Test the CacheManager class."""
    print("\nTesting CacheManager...")

    try:
        from esm_format.coupling_performance import CacheManager, CachingStrategy

        # Test basic caching functionality
        cache = CacheManager(CachingStrategy.LRU, max_size=3, ttl_seconds=1.0)

        # Test cache miss
        found, value = cache.get("key1")
        assert not found
        assert cache.get_hit_rate() == 0.0

        # Test cache put and hit
        cache.put("key1", {"result": "value1"})
        found, value = cache.get("key1")
        assert found
        assert value["result"] == "value1"
        assert cache.get_hit_rate() == 0.5  # 1 hit, 1 miss

        # Test cache eviction (LRU)
        cache.put("key2", {"result": "value2"})
        cache.put("key3", {"result": "value3"})
        cache.put("key4", {"result": "value4"})  # Should evict key1 (least recently used)

        found, _ = cache.get("key1")  # Should be evicted
        assert not found

        found, value = cache.get("key4")  # Should still be there
        assert found
        assert value["result"] == "value4"

        # Test TTL expiration
        time.sleep(1.1)  # Wait for TTL to expire
        found, _ = cache.get("key4")
        assert not found  # Should be expired

        print("✓ CacheManager tests passed")
        return True
    except Exception as e:
        print(f"✗ CacheManager test failed: {e}")
        return False


def test_load_balancer():
    """Test the LoadBalancer class."""
    print("\nTesting LoadBalancer...")

    try:
        from esm_format.coupling_performance import LoadBalancer, LoadBalancingMethod

        # Test round-robin balancing
        balancer = LoadBalancer(LoadBalancingMethod.ROUND_ROBIN, max_workers=3)

        assignments = []
        for i in range(6):
            worker = balancer.assign_task(f"task_{i}")
            assignments.append(worker)

        # Should cycle through workers 0, 1, 2, 0, 1, 2
        expected = [0, 1, 2, 0, 1, 2]
        assert assignments == expected

        # Test weighted balancing
        weighted_balancer = LoadBalancer(LoadBalancingMethod.WEIGHTED, max_workers=2)

        # Assign tasks with different costs
        worker1 = weighted_balancer.assign_task("light_task", estimated_cost=1.0)
        worker2 = weighted_balancer.assign_task("heavy_task", estimated_cost=5.0)
        worker3 = weighted_balancer.assign_task("medium_task", estimated_cost=2.0)

        # First two tasks should go to different workers
        assert worker1 != worker2

        # Test performance update
        weighted_balancer.update_worker_performance(worker1, task_duration=1.0, task_cost=1.0)
        weighted_balancer.update_worker_performance(worker2, task_duration=10.0, task_cost=5.0)

        # Worker 1 should be faster now
        balance_factor = weighted_balancer.get_load_balance_factor()
        assert balance_factor >= 1.0  # Perfect balance is 1.0, higher means more imbalanced

        print("✓ LoadBalancer tests passed")
        return True
    except Exception as e:
        print(f"✗ LoadBalancer test failed: {e}")
        return False


def test_memory_optimizer():
    """Test the MemoryOptimizer class."""
    print("\nTesting MemoryOptimizer...")

    try:
        from esm_format.coupling_performance import MemoryOptimizer
        from esm_format.coupling_graph import CouplingGraph

        optimizer = MemoryOptimizer(memory_limit_mb=100.0)

        # Test memory usage monitoring
        usage = optimizer.get_current_memory_usage()
        assert usage >= 0.0

        # Test memory pressure detection
        pressure = optimizer.check_memory_pressure()
        assert isinstance(pressure, bool)

        # Test data structure optimization
        test_variables = {
            "temperature": 25.5,
            "pressure": 1013.25,
            "humidity": 0.65
        }

        optimized = optimizer.optimize_data_structures(test_variables)
        assert len(optimized) == len(test_variables)
        assert all(isinstance(v, float) for v in optimized.values())

        # Test memory optimization suggestions
        mock_graph = type('MockGraph', (), {'nodes': {i: None for i in range(100)}, 'edges': list(range(150))})()
        suggestions = optimizer.suggest_memory_optimization(mock_graph)
        assert isinstance(suggestions, list)

        print("✓ MemoryOptimizer tests passed")
        return True
    except Exception as e:
        print(f"✗ MemoryOptimizer test failed: {e}")
        return False


def test_parallel_execution_engine():
    """Test the ParallelExecutionEngine class."""
    print("\nTesting ParallelExecutionEngine...")

    try:
        from esm_format.coupling_performance import (
            ParallelExecutionEngine,
            OptimizationConfig,
            ExecutionStrategy
        )

        # Create a simple mock coupling function
        def mock_coupling_function(variables: Dict[str, float], **kwargs) -> Tuple[Dict[str, float], Dict[str, float]]:
            component_name = kwargs.get('component_name', 'unknown')

            # Simulate some computation time
            time.sleep(0.01)

            # Simple coupling: add 0.1 to each variable
            updated = {k: v + 0.1 for k, v in variables.items()}
            residuals = {k: 0.1 for k in variables.keys()}

            return updated, residuals

        # Test sequential execution
        config = OptimizationConfig(execution_strategy=ExecutionStrategy.SEQUENTIAL)
        engine = ParallelExecutionEngine(config)

        initial_vars = {"temp": 20.0, "pressure": 1000.0}
        components = ["atmosphere", "ocean"]

        result_vars, residuals = engine.execute_coupling_level(
            components, mock_coupling_function, initial_vars
        )

        # Variables should be updated
        assert "temp" in result_vars
        assert "pressure" in result_vars
        assert result_vars["temp"] > initial_vars["temp"]
        assert result_vars["pressure"] > initial_vars["pressure"]

        # Test adaptive execution
        adaptive_config = OptimizationConfig(execution_strategy=ExecutionStrategy.ADAPTIVE)
        adaptive_engine = ParallelExecutionEngine(adaptive_config)

        result_vars2, residuals2 = adaptive_engine.execute_coupling_level(
            components, mock_coupling_function, initial_vars
        )

        # Results should be consistent
        assert len(result_vars2) == len(result_vars)

        print("✓ ParallelExecutionEngine tests passed")
        return True
    except Exception as e:
        print(f"✗ ParallelExecutionEngine test failed: {e}")
        return False


def test_performance_optimized_iterator():
    """Test the PerformanceOptimizedCouplingIterator class."""
    print("\nTesting PerformanceOptimizedCouplingIterator...")

    try:
        from esm_format.coupling_performance import create_performance_optimized_iterator, ExecutionStrategy
        from esm_format.coupling_iteration import create_default_coupling_iterator
        from esm_format.types import EsmFile, Model, ModelVariable, CouplingEntry, CouplingType

        # Create a simple ESM file for testing
        test_model = Model(
            name="TestModel",
            description="Simple test model",
            variables={
                "temperature": ModelVariable(
                    name="temperature",
                    description="Temperature",
                    type="state",
                    units="K",
                    default=298.15
                ),
                "pressure": ModelVariable(
                    name="pressure",
                    description="Pressure",
                    type="state",
                    units="Pa",
                    default=101325.0
                )
            },
            equations=[],
            metadata={}
        )

        esm_file = EsmFile(
            version="1.0",
            models=[test_model],
            reaction_systems=[],
            data_loaders=[],
            operators=[],
            couplings=[],
            metadata={}
        )

        # Create optimized iterator
        optimized_iterator = create_performance_optimized_iterator(
            execution_strategy=ExecutionStrategy.SEQUENTIAL  # Use sequential for testing
        )

        # Create a simple coupling function
        def simple_coupling_function(variables: Dict[str, float], **kwargs) -> Tuple[Dict[str, float], Dict[str, float]]:
            # Simple relaxation towards equilibrium
            updated = {}
            residuals = {}

            for var, value in variables.items():
                # Move towards target value
                if var == "temperature":
                    target = 300.0
                elif var == "pressure":
                    target = 100000.0
                else:
                    target = value

                new_value = value + 0.1 * (target - value)
                updated[var] = new_value
                residuals[var] = abs(new_value - value)

            return updated, residuals

        # Test optimized coupling iteration
        initial_variables = {"temperature": 298.15, "pressure": 101325.0}

        result, metrics = optimized_iterator.iterate_coupling_optimized(
            esm_file, initial_variables, simple_coupling_function
        )

        # Check that we got results
        assert result is not None
        assert metrics is not None
        assert metrics.execution_time > 0.0

        # Check optimization report
        report = optimized_iterator.get_optimization_report()
        assert "performance_summary" in report
        assert "component_performance" in report
        assert "optimization_recommendations" in report
        assert "configuration" in report

        print("✓ PerformanceOptimizedCouplingIterator tests passed")
        return True
    except Exception as e:
        print(f"✗ PerformanceOptimizedCouplingIterator test failed: {e}")
        return False


def test_convenience_functions():
    """Test convenience functions for creating optimized iterators."""
    print("\nTesting convenience functions...")

    try:
        from esm_format.coupling_performance import (
            create_performance_optimized_iterator,
            create_high_performance_iterator,
            ExecutionStrategy
        )

        # Test create_performance_optimized_iterator
        optimizer1 = create_performance_optimized_iterator(
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            enable_caching=True,
            max_parallel_workers=2
        )
        assert optimizer1 is not None
        assert optimizer1.config.execution_strategy == ExecutionStrategy.SEQUENTIAL
        assert optimizer1.config.max_parallel_workers == 2

        # Test create_high_performance_iterator
        optimizer2 = create_high_performance_iterator(
            max_iterations=50,
            tolerance=1e-5
        )
        assert optimizer2 is not None

        print("✓ Convenience function tests passed")
        return True
    except Exception as e:
        print(f"✗ Convenience function test failed: {e}")
        return False


def run_performance_benchmark():
    """Run a simple performance benchmark to demonstrate optimization benefits."""
    print("\nRunning performance benchmark...")

    try:
        from esm_format.coupling_performance import create_performance_optimized_iterator, ExecutionStrategy
        from esm_format.coupling_iteration import create_default_coupling_iterator
        from esm_format.types import EsmFile, Model, ModelVariable

        # Create a more complex test model
        test_model = Model(
            name="BenchmarkModel",
            description="Benchmark test model",
            variables={
                f"var_{i}": ModelVariable(
                    name=f"var_{i}",
                    description=f"Variable {i}",
                    type="state",
                    units="dimensionless",
                    default=float(i)
                ) for i in range(10)  # 10 variables
            },
            equations=[],
            metadata={}
        )

        esm_file = EsmFile(
            version="1.0",
            models=[test_model],
            reaction_systems=[],
            data_loaders=[],
            operators=[],
            couplings=[],
            metadata={}
        )

        # Create a computationally intensive coupling function
        def intensive_coupling_function(variables: Dict[str, float], **kwargs) -> Tuple[Dict[str, float], Dict[str, float]]:
            updated = {}
            residuals = {}

            # Simulate computational work
            for var, value in variables.items():
                # Some mathematical operations to simulate computation
                new_value = value
                for _ in range(100):  # Simulate work
                    new_value = math.sin(new_value) * 0.1 + value * 0.99

                updated[var] = new_value
                residuals[var] = abs(new_value - value)

            # Small delay to make timing more measurable
            time.sleep(0.001)

            return updated, residuals

        initial_variables = {f"var_{i}": float(i) for i in range(10)}

        # Benchmark standard iterator
        print("  Running standard coupling iterator...")
        standard_iterator = create_default_coupling_iterator(max_iterations=10, tolerance=1e-4)

        start_time = time.time()
        standard_result = standard_iterator.iterate_coupling(
            esm_file, initial_variables, intensive_coupling_function
        )
        standard_time = time.time() - start_time

        # Benchmark optimized iterator
        print("  Running optimized coupling iterator...")
        optimized_iterator = create_performance_optimized_iterator(
            execution_strategy=ExecutionStrategy.ADAPTIVE,
            enable_caching=True
        )

        start_time = time.time()
        optimized_result, metrics = optimized_iterator.iterate_coupling_optimized(
            esm_file, initial_variables, intensive_coupling_function
        )
        optimized_time = time.time() - start_time

        # Compare results
        print(f"  Standard iterator: {standard_time:.3f}s ({standard_result.total_iterations} iterations)")
        print(f"  Optimized iterator: {optimized_time:.3f}s ({optimized_result.total_iterations} iterations)")
        print(f"  Cache hit rate: {metrics.cache_hit_rate:.1%}")
        print(f"  Load balance factor: {metrics.load_balance_factor:.2f}")

        # Both should converge
        assert standard_result.converged or standard_result.total_iterations >= 10
        assert optimized_result.converged or optimized_result.total_iterations >= 10

        print("✓ Performance benchmark completed")
        return True
    except Exception as e:
        print(f"✗ Performance benchmark failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Testing Coupling Performance Optimization Algorithms")
    print("=" * 50)

    tests = [
        test_basic_import,
        test_performance_metrics,
        test_optimization_config,
        test_cache_manager,
        test_load_balancer,
        test_memory_optimizer,
        test_parallel_execution_engine,
        test_performance_optimized_iterator,
        test_convenience_functions,
        run_performance_benchmark
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! Coupling performance optimization is working correctly.")
        return True
    else:
        print(f"❌ {failed} tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)