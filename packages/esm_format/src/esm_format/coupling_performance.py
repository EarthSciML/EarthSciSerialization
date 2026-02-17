"""
Coupling performance optimization algorithms for ESM Format.

This module implements performance optimization strategies for coupling execution, including:
1. Parallel execution strategies for independent components
2. Load balancing algorithms for computational resources
3. Memory optimization techniques
4. Communication minimization strategies
5. Adaptive scheduling based on component characteristics
6. Caching and memoization for repeated computations

Integrates with existing coupling infrastructure to improve execution efficiency.
"""

# Optional import for multiprocessing and threading
try:
    import multiprocessing as mp
    from multiprocessing import Pool, Process, Queue, Event
    from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
    PARALLEL_AVAILABLE = True
except ImportError:
    PARALLEL_AVAILABLE = False

# Optional import for memory profiling
try:
    import psutil
    MEMORY_MONITORING_AVAILABLE = True
except ImportError:
    MEMORY_MONITORING_AVAILABLE = False
    # Fallback memory monitoring
    class psutil_fallback:
        @staticmethod
        def Process():
            class MockProcess:
                def memory_info(self):
                    return type('MemInfo', (), {'rss': 0})()
            return MockProcess()

        @staticmethod
        def virtual_memory():
            return type('VirtMem', (), {'total': 8 * 1024**3, 'available': 4 * 1024**3})()

    psutil = psutil_fallback()

import time
import logging
import hashlib
import pickle
from typing import Dict, List, Optional, Tuple, Union, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import threading
from abc import ABC, abstractmethod

from .coupling_graph import CouplingGraph, CouplingNode, construct_coupling_graph
from .coupling_iteration import CouplingIterator, ConvergenceConfig, CouplingResult, IterationState
from .esm_types import EsmFile


logger = logging.getLogger(__name__)


class ExecutionStrategy(Enum):
    """Strategies for parallel execution of coupling components."""
    SEQUENTIAL = "sequential"          # Execute components one by one
    LEVEL_PARALLEL = "level_parallel"  # Parallelize within dependency levels
    FULL_PARALLEL = "full_parallel"    # Maximum parallelization with dependencies
    ADAPTIVE = "adaptive"              # Choose strategy based on system characteristics
    HYBRID = "hybrid"                  # Mix of parallel and sequential based on load


class LoadBalancingMethod(Enum):
    """Methods for balancing computational load across resources."""
    ROUND_ROBIN = "round_robin"        # Distribute tasks in round-robin fashion
    WEIGHTED = "weighted"              # Weight by estimated computational cost
    DYNAMIC = "dynamic"                # Dynamic load balancing based on actual performance
    WORK_STEALING = "work_stealing"    # Allow idle workers to steal work
    LOCALITY_AWARE = "locality_aware"  # Consider data locality and memory access patterns


class CachingStrategy(Enum):
    """Strategies for caching coupling computations."""
    NONE = "none"                      # No caching
    FUNCTION_LEVEL = "function_level"  # Cache individual function results
    ITERATION_LEVEL = "iteration_level" # Cache full iteration results
    ADAPTIVE = "adaptive"              # Adaptively choose what to cache
    LRU = "lru"                        # Least Recently Used caching


@dataclass
class PerformanceMetrics:
    """Metrics for tracking coupling performance."""
    execution_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_utilization: float = 0.0
    cache_hit_rate: float = 0.0
    parallel_efficiency: float = 0.0
    communication_overhead: float = 0.0
    load_balance_factor: float = 1.0  # 1.0 = perfect balance, >1.0 = imbalanced
    component_times: Dict[str, float] = field(default_factory=dict)
    iteration_times: List[float] = field(default_factory=list)
    memory_peaks: List[float] = field(default_factory=list)

    def add_component_time(self, component: str, duration: float):
        """Add timing for a component."""
        if component not in self.component_times:
            self.component_times[component] = 0.0
        self.component_times[component] += duration

    def add_iteration_time(self, duration: float):
        """Add timing for an iteration."""
        self.iteration_times.append(duration)

    def get_average_iteration_time(self) -> float:
        """Get average iteration time."""
        return sum(self.iteration_times) / len(self.iteration_times) if self.iteration_times else 0.0

    def get_slowest_components(self, n: int = 3) -> List[Tuple[str, float]]:
        """Get the n slowest components."""
        return sorted(self.component_times.items(), key=lambda x: x[1], reverse=True)[:n]


@dataclass
class OptimizationConfig:
    """Configuration for coupling performance optimization."""
    execution_strategy: ExecutionStrategy = ExecutionStrategy.ADAPTIVE
    load_balancing: LoadBalancingMethod = LoadBalancingMethod.DYNAMIC
    caching_strategy: CachingStrategy = CachingStrategy.ADAPTIVE
    max_parallel_workers: int = 0  # 0 = use CPU count
    memory_limit_mb: float = 1000.0
    cache_size_limit: int = 100
    enable_profiling: bool = True
    communication_timeout: float = 5.0
    load_balance_threshold: float = 0.3  # Trigger rebalancing if load variance > this
    cache_ttl_seconds: float = 300.0  # Time-to-live for cached results


@dataclass
class ComponentProfile:
    """Performance profile for a coupling component."""
    name: str
    average_execution_time: float = 0.0
    memory_footprint: float = 0.0
    cpu_intensity: float = 1.0  # Relative CPU usage
    io_intensity: float = 0.0   # Relative I/O usage
    communication_cost: float = 0.0  # Cost of data transfer
    reliability_score: float = 1.0   # Historical success rate
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    last_update: float = field(default_factory=time.time)

    def update_profile(self, execution_time: float, memory_mb: float, success: bool):
        """Update profile based on recent execution."""
        alpha = 0.1  # Learning rate for exponential moving average

        if self.average_execution_time == 0.0:
            self.average_execution_time = execution_time
        else:
            self.average_execution_time = (1 - alpha) * self.average_execution_time + alpha * execution_time

        if self.memory_footprint == 0.0:
            self.memory_footprint = memory_mb
        else:
            self.memory_footprint = (1 - alpha) * self.memory_footprint + alpha * memory_mb

        # Update reliability score
        if success:
            self.reliability_score = min(1.0, self.reliability_score + 0.01)
        else:
            self.reliability_score = max(0.0, self.reliability_score - 0.05)

        self.last_update = time.time()


class MemoryOptimizer:
    """Optimizes memory usage during coupling execution."""

    def __init__(self, memory_limit_mb: float = 1000.0):
        self.memory_limit_mb = memory_limit_mb
        self.current_usage_mb = 0.0
        self.peak_usage_mb = 0.0

    def get_current_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # Convert bytes to MB
        except:
            return 0.0

    def check_memory_pressure(self) -> bool:
        """Check if we're approaching memory limits."""
        current_usage = self.get_current_memory_usage()
        self.current_usage_mb = current_usage
        self.peak_usage_mb = max(self.peak_usage_mb, current_usage)

        return current_usage > (0.8 * self.memory_limit_mb)

    def suggest_memory_optimization(self, coupling_graph: CouplingGraph) -> List[str]:
        """Suggest memory optimization strategies."""
        suggestions = []

        if self.check_memory_pressure():
            suggestions.append("Memory pressure detected - consider reducing batch sizes")
            suggestions.append("Enable more aggressive garbage collection")
            suggestions.append("Consider streaming data instead of loading all at once")

            # Analyze graph for memory-intensive patterns
            if len(coupling_graph.nodes) > 50:
                suggestions.append("Large coupling graph detected - consider hierarchical execution")

            if len(coupling_graph.edges) > 100:
                suggestions.append("High coupling complexity - consider component consolidation")

        return suggestions

    def optimize_data_structures(self, variables: Dict[str, float]) -> Dict[str, float]:
        """Optimize data structures for memory efficiency."""
        # For now, just ensure we're using the most memory-efficient representations
        optimized = {}
        for key, value in variables.items():
            # Convert to native Python float for memory efficiency
            optimized[key] = float(value)
        return optimized


class CacheManager:
    """Manages caching of coupling computations."""

    def __init__(self, strategy: CachingStrategy = CachingStrategy.ADAPTIVE,
                 max_size: int = 100, ttl_seconds: float = 300.0):
        self.strategy = strategy
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, timestamp)
        self.hit_count = 0
        self.miss_count = 0
        self.access_times: Dict[str, float] = {}  # For LRU
        self.lock = threading.Lock()

    def _generate_cache_key(self, function_name: str, args: Tuple, kwargs: Dict) -> str:
        """Generate a cache key for function arguments."""
        try:
            # Create a hash of the function signature
            key_data = (function_name, args, tuple(sorted(kwargs.items())))
            return hashlib.md5(str(key_data).encode()).hexdigest()
        except:
            # Fallback for non-hashable arguments
            return f"{function_name}_{id(args)}_{id(kwargs)}"

    def get(self, key: str) -> Tuple[bool, Any]:
        """Get value from cache."""
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]

                # Check TTL
                if time.time() - timestamp <= self.ttl_seconds:
                    self.hit_count += 1
                    self.access_times[key] = time.time()
                    return True, value
                else:
                    # Expired
                    del self.cache[key]
                    if key in self.access_times:
                        del self.access_times[key]

            self.miss_count += 1
            return False, None

    def put(self, key: str, value: Any):
        """Put value in cache."""
        with self.lock:
            # Check size limits
            if len(self.cache) >= self.max_size:
                self._evict_items()

            self.cache[key] = (value, time.time())
            self.access_times[key] = time.time()

    def _evict_items(self):
        """Evict items based on caching strategy."""
        if self.strategy == CachingStrategy.LRU:
            # Remove least recently used
            if self.access_times:
                oldest_key = min(self.access_times.items(), key=lambda x: x[1])[0]
                if oldest_key in self.cache:
                    del self.cache[oldest_key]
                del self.access_times[oldest_key]
        else:
            # Remove oldest by timestamp
            if self.cache:
                oldest_key = min(self.cache.items(), key=lambda x: x[1][1])[0]
                del self.cache[oldest_key]
                if oldest_key in self.access_times:
                    del self.access_times[oldest_key]

    def get_hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0

    def clear(self):
        """Clear cache."""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            self.hit_count = 0
            self.miss_count = 0


class LoadBalancer:
    """Balances computational load across available resources."""

    def __init__(self, method: LoadBalancingMethod = LoadBalancingMethod.DYNAMIC,
                 max_workers: int = 0):
        self.method = method
        self.max_workers = max_workers or mp.cpu_count()
        self.worker_loads: Dict[int, float] = {}
        self.worker_performance: Dict[int, float] = {}  # Tasks per second
        self.task_queue: deque = deque()

    def assign_task(self, task_id: str, estimated_cost: float = 1.0) -> int:
        """Assign a task to the best available worker."""
        if self.method == LoadBalancingMethod.ROUND_ROBIN:
            return self._round_robin_assignment()
        elif self.method == LoadBalancingMethod.WEIGHTED:
            return self._weighted_assignment(estimated_cost)
        elif self.method == LoadBalancingMethod.DYNAMIC:
            return self._dynamic_assignment(estimated_cost)
        else:
            return 0  # Fallback to single worker

    def _round_robin_assignment(self) -> int:
        """Simple round-robin task assignment."""
        if not hasattr(self, '_current_worker'):
            self._current_worker = 0

        worker_id = self._current_worker
        self._current_worker = (self._current_worker + 1) % self.max_workers
        return worker_id

    def _weighted_assignment(self, estimated_cost: float) -> int:
        """Assign based on estimated task cost and worker capacity."""
        if not self.worker_loads:
            # Initialize worker loads
            for i in range(self.max_workers):
                self.worker_loads[i] = 0.0

        # Find worker with minimum load
        best_worker = min(self.worker_loads.items(), key=lambda x: x[1])[0]
        self.worker_loads[best_worker] += estimated_cost
        return best_worker

    def _dynamic_assignment(self, estimated_cost: float) -> int:
        """Dynamic assignment based on actual worker performance."""
        if not self.worker_performance:
            # Initialize with equal performance assumptions
            for i in range(self.max_workers):
                self.worker_performance[i] = 1.0
                self.worker_loads[i] = 0.0

        # Choose worker based on performance and current load
        best_worker = 0
        best_score = float('inf')

        for worker_id in range(self.max_workers):
            performance = self.worker_performance[worker_id]
            current_load = self.worker_loads.get(worker_id, 0.0)

            # Score = estimated completion time
            score = (current_load + estimated_cost) / performance

            if score < best_score:
                best_score = score
                best_worker = worker_id

        self.worker_loads[best_worker] = self.worker_loads.get(best_worker, 0.0) + estimated_cost
        return best_worker

    def update_worker_performance(self, worker_id: int, task_duration: float, task_cost: float = 1.0):
        """Update worker performance based on completed task."""
        if task_duration > 0:
            performance = task_cost / task_duration  # Tasks per second

            if worker_id in self.worker_performance:
                # Exponential moving average
                alpha = 0.1
                self.worker_performance[worker_id] = (
                    (1 - alpha) * self.worker_performance[worker_id] + alpha * performance
                )
            else:
                self.worker_performance[worker_id] = performance

            # Update load
            self.worker_loads[worker_id] = max(0.0,
                self.worker_loads.get(worker_id, 0.0) - task_cost)

    def get_load_balance_factor(self) -> float:
        """Calculate load balance factor (1.0 = perfect, higher = more imbalanced)."""
        if not self.worker_loads:
            return 1.0

        loads = list(self.worker_loads.values())
        if not loads or all(load == 0 for load in loads):
            return 1.0

        mean_load = sum(loads) / len(loads)
        if mean_load == 0:
            return 1.0

        variance = sum((load - mean_load) ** 2 for load in loads) / len(loads)
        return 1.0 + variance / (mean_load ** 2)


class ParallelExecutionEngine:
    """Manages parallel execution of coupling components."""

    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.load_balancer = LoadBalancer(config.load_balancing, config.max_parallel_workers)
        self.component_profiles: Dict[str, ComponentProfile] = {}

    def execute_coupling_level(self,
                               level_components: List[str],
                               coupling_function: Callable,
                               variables: Dict[str, float],
                               **kwargs) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Execute all components in a dependency level in parallel."""

        if not PARALLEL_AVAILABLE or len(level_components) <= 1:
            return self._sequential_execution(level_components, coupling_function, variables, **kwargs)

        if self.config.execution_strategy == ExecutionStrategy.SEQUENTIAL:
            return self._sequential_execution(level_components, coupling_function, variables, **kwargs)
        elif self.config.execution_strategy in [ExecutionStrategy.LEVEL_PARALLEL, ExecutionStrategy.FULL_PARALLEL]:
            return self._parallel_execution(level_components, coupling_function, variables, **kwargs)
        else:  # ADAPTIVE or HYBRID
            return self._adaptive_execution(level_components, coupling_function, variables, **kwargs)

    def _sequential_execution(self,
                             components: List[str],
                             coupling_function: Callable,
                             variables: Dict[str, float],
                             **kwargs) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Execute components sequentially."""
        updated_variables = variables.copy()
        all_residuals = {}

        for component in components:
            start_time = time.time()

            try:
                # Execute component coupling
                component_kwargs = {**kwargs, 'component_name': component}
                result_vars, residuals = coupling_function(updated_variables, **component_kwargs)

                # Update variables with results
                updated_variables.update(result_vars)
                all_residuals.update(residuals or {})

                # Update component profile
                duration = time.time() - start_time
                memory_usage = self._get_memory_usage()
                self._update_component_profile(component, duration, memory_usage, True)

            except Exception as e:
                duration = time.time() - start_time
                self._update_component_profile(component, duration, 0.0, False)
                logger.warning(f"Component {component} failed: {e}")
                # Continue with other components

        return updated_variables, all_residuals

    def _parallel_execution(self,
                           components: List[str],
                           coupling_function: Callable,
                           variables: Dict[str, float],
                           **kwargs) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Execute components in parallel using multiprocessing."""

        max_workers = min(len(components), self.config.max_parallel_workers)
        updated_variables = variables.copy()
        all_residuals = {}

        try:
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Submit all component tasks
                future_to_component = {}

                for component in components:
                    component_kwargs = {**kwargs, 'component_name': component}
                    future = executor.submit(
                        self._execute_single_component,
                        coupling_function,
                        variables,
                        component,
                        component_kwargs
                    )
                    future_to_component[future] = component

                # Collect results
                for future in as_completed(future_to_component, timeout=self.config.communication_timeout):
                    component = future_to_component[future]

                    try:
                        result_vars, residuals, duration, success = future.result()

                        if success:
                            updated_variables.update(result_vars)
                            all_residuals.update(residuals or {})

                        # Update performance metrics
                        worker_id = self.load_balancer.assign_task(component, 1.0)
                        self.load_balancer.update_worker_performance(worker_id, duration, 1.0)

                        memory_usage = self._get_memory_usage()
                        self._update_component_profile(component, duration, memory_usage, success)

                    except Exception as e:
                        logger.error(f"Failed to get result for component {component}: {e}")
                        self._update_component_profile(component, 0.0, 0.0, False)

        except Exception as e:
            logger.error(f"Parallel execution failed: {e}")
            # Fallback to sequential execution
            return self._sequential_execution(components, coupling_function, variables, **kwargs)

        return updated_variables, all_residuals

    def _adaptive_execution(self,
                           components: List[str],
                           coupling_function: Callable,
                           variables: Dict[str, float],
                           **kwargs) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Adaptively choose between sequential and parallel execution."""

        # Decision criteria for adaptive execution
        num_components = len(components)

        # Check if parallel execution is beneficial
        if num_components < 2:
            return self._sequential_execution(components, coupling_function, variables, **kwargs)

        # Estimate overhead vs benefit
        estimated_parallel_benefit = self._estimate_parallel_benefit(components)
        parallel_overhead = 0.1 * num_components  # Estimated overhead per component

        if estimated_parallel_benefit > parallel_overhead:
            logger.debug(f"Using parallel execution for {num_components} components")
            return self._parallel_execution(components, coupling_function, variables, **kwargs)
        else:
            logger.debug(f"Using sequential execution for {num_components} components")
            return self._sequential_execution(components, coupling_function, variables, **kwargs)

    def _estimate_parallel_benefit(self, components: List[str]) -> float:
        """Estimate benefit of parallel execution for given components."""
        total_estimated_time = 0.0
        max_component_time = 0.0

        for component in components:
            if component in self.component_profiles:
                exec_time = self.component_profiles[component].average_execution_time
            else:
                exec_time = 1.0  # Default assumption

            total_estimated_time += exec_time
            max_component_time = max(max_component_time, exec_time)

        # Parallel benefit = sequential time - parallel time (limited by slowest component)
        estimated_parallel_time = max_component_time
        return max(0.0, total_estimated_time - estimated_parallel_time)

    def _execute_single_component(self,
                                  coupling_function: Callable,
                                  variables: Dict[str, float],
                                  component: str,
                                  component_kwargs: Dict) -> Tuple[Dict[str, float], Dict[str, float], float, bool]:
        """Execute a single component (for multiprocessing)."""
        start_time = time.time()

        try:
            result_vars, residuals = coupling_function(variables, **component_kwargs)
            duration = time.time() - start_time
            return result_vars, residuals, duration, True
        except Exception as e:
            duration = time.time() - start_time
            logger.warning(f"Component {component} execution failed: {e}")
            return variables, {}, duration, False

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0

    def _update_component_profile(self, component: str, duration: float, memory_mb: float, success: bool):
        """Update performance profile for a component."""
        if component not in self.component_profiles:
            self.component_profiles[component] = ComponentProfile(component)

        self.component_profiles[component].update_profile(duration, memory_mb, success)


class PerformanceOptimizedCouplingIterator:
    """
    Coupling iterator with comprehensive performance optimizations.

    This class extends the standard coupling iteration with:
    - Parallel execution of independent components
    - Load balancing across computational resources
    - Memory optimization and monitoring
    - Intelligent caching of computations
    - Adaptive optimization strategies
    """

    def __init__(self,
                 base_iterator: CouplingIterator,
                 optimization_config: Optional[OptimizationConfig] = None):
        self.base_iterator = base_iterator
        self.config = optimization_config or OptimizationConfig()

        # Initialize optimization components
        self.parallel_engine = ParallelExecutionEngine(self.config)
        self.memory_optimizer = MemoryOptimizer(self.config.memory_limit_mb)
        self.cache_manager = CacheManager(
            self.config.caching_strategy,
            self.config.cache_size_limit,
            self.config.cache_ttl_seconds
        )

        # Performance tracking
        self.performance_metrics = PerformanceMetrics()
        self.optimization_enabled = True

        logger.info(f"Initialized PerformanceOptimizedCouplingIterator with "
                   f"{self.config.execution_strategy.value} execution, "
                   f"{self.config.load_balancing.value} load balancing, "
                   f"{self.config.caching_strategy.value} caching")

    def iterate_coupling_optimized(self,
                                   esm_file: EsmFile,
                                   initial_variables: Dict[str, float],
                                   coupling_function: Callable,
                                   **kwargs) -> Tuple[CouplingResult, PerformanceMetrics]:
        """
        Perform optimized coupling iteration.

        Args:
            esm_file: ESM file defining the coupled system
            initial_variables: Initial values for coupled variables
            coupling_function: Function that performs coupling for components
            **kwargs: Additional arguments for the coupling function

        Returns:
            Tuple of (CouplingResult, PerformanceMetrics)
        """
        start_time = time.time()

        try:
            # Build coupling graph for optimization analysis
            coupling_graph = construct_coupling_graph(esm_file)
            logger.info(f"Analyzing coupling graph with {len(coupling_graph.nodes)} nodes")

            # Get execution order with dependency levels
            execution_levels = self._analyze_execution_levels(coupling_graph)
            logger.info(f"Identified {len(execution_levels)} execution levels")

            # Create optimized coupling function
            optimized_coupling_function = self._create_optimized_coupling_function(
                coupling_function, execution_levels
            )

            # Perform iterative coupling with optimization
            result = self.base_iterator.iterate_coupling(
                esm_file, initial_variables, optimized_coupling_function, **kwargs
            )

            # Finalize performance metrics
            execution_time = time.time() - start_time
            self._finalize_performance_metrics(result, execution_time, coupling_graph)

            return result, self.performance_metrics

        except Exception as e:
            logger.error(f"Optimized coupling iteration failed: {e}")
            # Fallback to standard iteration
            result = self.base_iterator.iterate_coupling(
                esm_file, initial_variables, coupling_function, **kwargs
            )
            execution_time = time.time() - start_time
            self.performance_metrics.execution_time = execution_time
            return result, self.performance_metrics

    def _analyze_execution_levels(self, coupling_graph: CouplingGraph) -> List[List[str]]:
        """Analyze coupling graph to determine execution levels for parallelization."""

        # Get execution order from coupling graph
        execution_order = coupling_graph.get_execution_order()

        # Group components by dependency level
        levels = []
        current_level = []

        for component_id in execution_order:
            dep_info = coupling_graph.get_dependency_info(component_id)

            if dep_info is None:
                # No dependency info - put in current level
                current_level.append(component_id)
            else:
                # Check if we need to start a new level
                if dep_info.dependency_level > len(levels):
                    # Finish current level
                    if current_level:
                        levels.append(current_level)
                    current_level = [component_id]
                else:
                    current_level.append(component_id)

        # Add final level
        if current_level:
            levels.append(current_level)

        return levels

    def _create_optimized_coupling_function(self,
                                            original_function: Callable,
                                            execution_levels: List[List[str]]) -> Callable:
        """Create an optimized coupling function that uses performance optimizations."""

        def optimized_function(variables: Dict[str, float], **kwargs) -> Tuple[Dict[str, float], Dict[str, float]]:
            iteration_start_time = time.time()

            # Check for cached result
            if self.config.caching_strategy != CachingStrategy.NONE:
                cache_key = self._generate_iteration_cache_key(variables, kwargs)
                cached, cached_result = self.cache_manager.get(cache_key)
                if cached:
                    logger.debug("Using cached coupling result")
                    return cached_result

            # Memory optimization
            if self.config.enable_profiling:
                memory_pressure = self.memory_optimizer.check_memory_pressure()
                if memory_pressure:
                    logger.warning("Memory pressure detected - applying optimizations")
                    variables = self.memory_optimizer.optimize_data_structures(variables)

            updated_variables = variables.copy()
            all_residuals = {}

            # Execute each dependency level
            for level_idx, level_components in enumerate(execution_levels):
                level_start_time = time.time()

                logger.debug(f"Executing level {level_idx + 1} with {len(level_components)} components")

                # Execute components in this level (potentially in parallel)
                level_vars, level_residuals = self.parallel_engine.execute_coupling_level(
                    level_components, original_function, updated_variables, **kwargs
                )

                # Update overall results
                updated_variables.update(level_vars)
                all_residuals.update(level_residuals)

                # Track level performance
                level_duration = time.time() - level_start_time
                self.performance_metrics.add_iteration_time(level_duration)

                logger.debug(f"Level {level_idx + 1} completed in {level_duration:.3f}s")

            # Cache result if caching is enabled
            if self.config.caching_strategy != CachingStrategy.NONE:
                result = (updated_variables, all_residuals)
                self.cache_manager.put(cache_key, result)

            # Update performance metrics
            iteration_duration = time.time() - iteration_start_time
            self.performance_metrics.add_iteration_time(iteration_duration)

            return updated_variables, all_residuals

        return optimized_function

    def _generate_iteration_cache_key(self, variables: Dict[str, float], kwargs: Dict) -> str:
        """Generate cache key for iteration."""
        try:
            # Create a simplified cache key based on variable values
            var_hash = hashlib.md5(str(sorted(variables.items())).encode()).hexdigest()
            kwarg_hash = hashlib.md5(str(sorted(kwargs.items())).encode()).hexdigest()
            return f"iteration_{var_hash}_{kwarg_hash}"
        except:
            return f"iteration_{id(variables)}_{id(kwargs)}"

    def _finalize_performance_metrics(self,
                                      result: CouplingResult,
                                      total_time: float,
                                      coupling_graph: CouplingGraph):
        """Finalize performance metrics after coupling completion."""

        self.performance_metrics.execution_time = total_time
        self.performance_metrics.cache_hit_rate = self.cache_manager.get_hit_rate()
        self.performance_metrics.load_balance_factor = self.parallel_engine.load_balancer.get_load_balance_factor()

        # Memory metrics
        self.performance_metrics.memory_usage_mb = self.memory_optimizer.current_usage_mb
        self.performance_metrics.memory_peaks.append(self.memory_optimizer.peak_usage_mb)

        # Component performance analysis
        for component_name, profile in self.parallel_engine.component_profiles.items():
            self.performance_metrics.add_component_time(component_name, profile.average_execution_time)

        # Parallel efficiency calculation
        if len(self.performance_metrics.iteration_times) > 1:
            avg_iteration_time = self.performance_metrics.get_average_iteration_time()
            theoretical_sequential_time = sum(
                profile.average_execution_time
                for profile in self.parallel_engine.component_profiles.values()
            )

            if theoretical_sequential_time > 0 and avg_iteration_time > 0:
                self.performance_metrics.parallel_efficiency = (
                    theoretical_sequential_time / (avg_iteration_time * self.config.max_parallel_workers)
                )

        logger.info(f"Coupling completed in {total_time:.2f}s with "
                   f"{result.total_iterations} iterations, "
                   f"cache hit rate: {self.performance_metrics.cache_hit_rate:.1%}, "
                   f"load balance factor: {self.performance_metrics.load_balance_factor:.2f}")

    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate a comprehensive optimization report."""

        report = {
            "performance_summary": {
                "total_execution_time": self.performance_metrics.execution_time,
                "average_iteration_time": self.performance_metrics.get_average_iteration_time(),
                "cache_hit_rate": self.performance_metrics.cache_hit_rate,
                "parallel_efficiency": self.performance_metrics.parallel_efficiency,
                "load_balance_factor": self.performance_metrics.load_balance_factor,
                "peak_memory_usage_mb": max(self.performance_metrics.memory_peaks) if self.performance_metrics.memory_peaks else 0.0
            },

            "component_performance": dict(self.performance_metrics.component_times),

            "slowest_components": self.performance_metrics.get_slowest_components(),

            "optimization_recommendations": self._generate_optimization_recommendations(),

            "configuration": {
                "execution_strategy": self.config.execution_strategy.value,
                "load_balancing": self.config.load_balancing.value,
                "caching_strategy": self.config.caching_strategy.value,
                "max_parallel_workers": self.config.max_parallel_workers,
                "memory_limit_mb": self.config.memory_limit_mb
            }
        }

        return report

    def _generate_optimization_recommendations(self) -> List[str]:
        """Generate recommendations for further optimization."""
        recommendations = []

        # Cache performance
        if self.performance_metrics.cache_hit_rate < 0.5:
            recommendations.append("Low cache hit rate - consider increasing cache size or adjusting caching strategy")

        # Load balancing
        if self.performance_metrics.load_balance_factor > 1.5:
            recommendations.append("Poor load balancing detected - consider dynamic load balancing or work stealing")

        # Parallel efficiency
        if self.performance_metrics.parallel_efficiency < 0.5:
            recommendations.append("Low parallel efficiency - check for bottlenecks or consider sequential execution")

        # Component performance
        slowest = self.performance_metrics.get_slowest_components(1)
        if slowest:
            component_name, duration = slowest[0]
            recommendations.append(f"Component '{component_name}' is the bottleneck ({duration:.2f}s) - consider optimization")

        # Memory usage
        if self.performance_metrics.memory_peaks:
            peak_memory = max(self.performance_metrics.memory_peaks)
            if peak_memory > 0.8 * self.config.memory_limit_mb:
                recommendations.append(f"High memory usage ({peak_memory:.1f}MB) - consider memory optimization")

        # Memory optimizer suggestions
        memory_suggestions = self.memory_optimizer.suggest_memory_optimization(
            # We don't have direct access to the coupling graph here, so create a mock one
            type('MockGraph', (), {'nodes': {}, 'edges': []})()
        )
        recommendations.extend(memory_suggestions)

        return recommendations


# Convenience functions for creating optimized iterators

def create_performance_optimized_iterator(
    base_iterator: Optional[CouplingIterator] = None,
    execution_strategy: ExecutionStrategy = ExecutionStrategy.ADAPTIVE,
    enable_caching: bool = True,
    max_parallel_workers: int = 0
) -> PerformanceOptimizedCouplingIterator:
    """
    Create a performance-optimized coupling iterator with sensible defaults.

    Args:
        base_iterator: Base coupling iterator (creates default if None)
        execution_strategy: Strategy for parallel execution
        enable_caching: Whether to enable result caching
        max_parallel_workers: Maximum parallel workers (0 = CPU count)

    Returns:
        Configured PerformanceOptimizedCouplingIterator
    """
    if base_iterator is None:
        # Create a default base iterator
        from .coupling_iteration import create_default_coupling_iterator
        base_iterator = create_default_coupling_iterator()

    optimization_config = OptimizationConfig(
        execution_strategy=execution_strategy,
        load_balancing=LoadBalancingMethod.DYNAMIC,
        caching_strategy=CachingStrategy.ADAPTIVE if enable_caching else CachingStrategy.NONE,
        max_parallel_workers=max_parallel_workers or mp.cpu_count() if PARALLEL_AVAILABLE else 1,
        enable_profiling=True
    )

    return PerformanceOptimizedCouplingIterator(base_iterator, optimization_config)


def create_high_performance_iterator(
    max_iterations: int = 100,
    tolerance: float = 1e-6
) -> PerformanceOptimizedCouplingIterator:
    """
    Create a high-performance iterator optimized for speed and efficiency.

    Args:
        max_iterations: Maximum coupling iterations
        tolerance: Convergence tolerance

    Returns:
        High-performance PerformanceOptimizedCouplingIterator
    """
    from .coupling_iteration import create_default_coupling_iterator

    base_iterator = create_default_coupling_iterator(
        max_iterations=max_iterations,
        tolerance=tolerance,
        use_acceleration=True
    )

    optimization_config = OptimizationConfig(
        execution_strategy=ExecutionStrategy.FULL_PARALLEL,
        load_balancing=LoadBalancingMethod.WORK_STEALING,
        caching_strategy=CachingStrategy.LRU,
        max_parallel_workers=mp.cpu_count() if PARALLEL_AVAILABLE else 1,
        memory_limit_mb=2000.0,
        cache_size_limit=200,
        enable_profiling=True
    )

    return PerformanceOptimizedCouplingIterator(base_iterator, optimization_config)


# Export main classes and functions
__all__ = [
    'ExecutionStrategy', 'LoadBalancingMethod', 'CachingStrategy',
    'PerformanceMetrics', 'OptimizationConfig', 'ComponentProfile',
    'MemoryOptimizer', 'CacheManager', 'LoadBalancer', 'ParallelExecutionEngine',
    'PerformanceOptimizedCouplingIterator', 'create_performance_optimized_iterator',
    'create_high_performance_iterator'
]