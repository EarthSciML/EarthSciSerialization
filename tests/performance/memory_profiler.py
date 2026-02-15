#!/usr/bin/env python3
"""
Memory profiling script for ESM format libraries.

This script provides detailed memory profiling for ESM parsing, serialization,
and validation operations to detect memory leaks and optimize memory usage.
"""

import os
import sys
import time
import json
import argparse
import tracemalloc
import gc
from pathlib import Path
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
from dataclasses import dataclass

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "esm_format" / "src"))

try:
    import psutil
except ImportError:
    print("Warning: psutil not available, some memory metrics will be unavailable")
    psutil = None

try:
    from esm_format import load, save
    from esm_format.types import EsmFile, Metadata, Model, ModelVariable, Equation, ExprNode
    ESM_FORMAT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: esm_format not available: {e}")
    ESM_FORMAT_AVAILABLE = False


@dataclass
class MemorySnapshot:
    """Represents a memory usage snapshot at a specific point in time."""
    timestamp: float
    rss_mb: float
    vms_mb: float
    peak_mb: float
    python_tracemalloc_mb: Optional[float] = None
    gc_objects: Optional[int] = None


class MemoryProfiler:
    """Advanced memory profiler for ESM operations."""

    def __init__(self, enable_tracemalloc: bool = True):
        self.enable_tracemalloc = enable_tracemalloc
        self.snapshots: List[MemorySnapshot] = []
        self.process = psutil.Process() if psutil else None

        if enable_tracemalloc:
            tracemalloc.start()

    def take_snapshot(self, label: str = "") -> MemorySnapshot:
        """Take a memory usage snapshot."""
        timestamp = time.time()

        # Get system memory info
        if self.process:
            memory_info = self.process.memory_info()
            rss_mb = memory_info.rss / 1024 / 1024
            vms_mb = memory_info.vms / 1024 / 1024

            # Get peak memory usage (Linux only)
            try:
                with open('/proc/self/status', 'r') as f:
                    for line in f:
                        if line.startswith('VmHWM:'):
                            peak_mb = float(line.split()[1]) / 1024
                            break
                    else:
                        peak_mb = rss_mb
            except (FileNotFoundError, PermissionError):
                peak_mb = rss_mb
        else:
            rss_mb = vms_mb = peak_mb = 0.0

        # Get Python tracemalloc info
        tracemalloc_mb = None
        if self.enable_tracemalloc and tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc_mb = current / 1024 / 1024

        # Get garbage collector info
        gc_objects = len(gc.get_objects())

        snapshot = MemorySnapshot(
            timestamp=timestamp,
            rss_mb=rss_mb,
            vms_mb=vms_mb,
            peak_mb=peak_mb,
            python_tracemalloc_mb=tracemalloc_mb,
            gc_objects=gc_objects
        )

        self.snapshots.append(snapshot)

        if label:
            print(f"Memory snapshot [{label}]: RSS={rss_mb:.1f}MB, "
                  f"Python={tracemalloc_mb or 0:.1f}MB, GC_objects={gc_objects}")

        return snapshot

    def get_memory_delta(self, start_snapshot: MemorySnapshot, end_snapshot: MemorySnapshot) -> Dict[str, float]:
        """Calculate memory usage delta between two snapshots."""
        return {
            'rss_delta_mb': end_snapshot.rss_mb - start_snapshot.rss_mb,
            'vms_delta_mb': end_snapshot.vms_mb - start_snapshot.vms_mb,
            'python_delta_mb': (
                (end_snapshot.python_tracemalloc_mb or 0) -
                (start_snapshot.python_tracemalloc_mb or 0)
            ),
            'gc_objects_delta': end_snapshot.gc_objects - start_snapshot.gc_objects,
            'duration_s': end_snapshot.timestamp - start_snapshot.timestamp
        }

    def detect_memory_leaks(self, threshold_mb: float = 10.0) -> List[Dict[str, Any]]:
        """Detect potential memory leaks by analyzing snapshot trends."""
        leaks = []

        if len(self.snapshots) < 3:
            return leaks

        # Look for consistent memory growth patterns
        window_size = min(5, len(self.snapshots))

        for i in range(window_size, len(self.snapshots)):
            recent_snapshots = self.snapshots[i-window_size:i+1]

            # Calculate linear trend for RSS memory
            rss_values = [s.rss_mb for s in recent_snapshots]
            if len(set(rss_values)) > 1:  # Not all the same value
                # Simple linear regression slope
                n = len(rss_values)
                x_mean = (n - 1) / 2
                y_mean = sum(rss_values) / n

                slope = sum((j - x_mean) * (rss_values[j] - y_mean) for j in range(n))
                slope /= sum((j - x_mean) ** 2 for j in range(n))

                # If consistently growing memory over threshold
                if slope > threshold_mb / window_size:
                    leaks.append({
                        'timestamp': recent_snapshots[-1].timestamp,
                        'growth_rate_mb_per_snapshot': slope,
                        'window_size': window_size,
                        'estimated_leak_mb_per_operation': slope,
                        'recent_rss_mb': recent_snapshots[-1].rss_mb
                    })

        return leaks

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive memory profiling report."""
        if not self.snapshots:
            return {'error': 'No memory snapshots taken'}

        first_snapshot = self.snapshots[0]
        last_snapshot = self.snapshots[-1]

        total_delta = self.get_memory_delta(first_snapshot, last_snapshot)

        # Calculate memory usage statistics
        rss_values = [s.rss_mb for s in self.snapshots]
        peak_rss = max(rss_values)
        min_rss = min(rss_values)
        avg_rss = sum(rss_values) / len(rss_values)

        python_values = [s.python_tracemalloc_mb for s in self.snapshots if s.python_tracemalloc_mb is not None]
        peak_python = max(python_values) if python_values else None

        # Detect leaks
        leaks = self.detect_memory_leaks()

        report = {
            'summary': {
                'total_duration_s': total_delta['duration_s'],
                'snapshots_taken': len(self.snapshots),
                'peak_rss_mb': peak_rss,
                'min_rss_mb': min_rss,
                'avg_rss_mb': avg_rss,
                'total_rss_delta_mb': total_delta['rss_delta_mb'],
                'peak_python_mb': peak_python
            },
            'memory_efficiency': {
                'memory_overhead_ratio': (peak_rss - min_rss) / min_rss if min_rss > 0 else 0,
                'gc_objects_growth': total_delta['gc_objects_delta'],
                'python_memory_delta_mb': total_delta['python_delta_mb']
            },
            'leak_detection': {
                'potential_leaks_found': len(leaks),
                'leaks': leaks
            },
            'raw_snapshots': [
                {
                    'timestamp': s.timestamp,
                    'rss_mb': s.rss_mb,
                    'python_mb': s.python_tracemalloc_mb,
                    'gc_objects': s.gc_objects
                }
                for s in self.snapshots
            ]
        }

        return report


def create_test_esm_file(size_category: str = "small") -> Optional[EsmFile]:
    """Create test ESM file of specified size."""
    if not ESM_FORMAT_AVAILABLE:
        return None

    if size_category == "small":
        # Small test file
        variables = {
            "x": ModelVariable(type="state", units="m", default=1.0),
            "y": ModelVariable(type="state", units="m/s", default=0.0),
            "k": ModelVariable(type="parameter", units="1/s", default=0.1)
        }

        equations = [
            Equation(
                lhs=ExprNode(op="D", args=["x"], wrt="t"),
                rhs="y"
            ),
            Equation(
                lhs=ExprNode(op="D", args=["y"], wrt="t"),
                rhs=ExprNode(op="*", args=[ExprNode(op="-", args=["k"]), "x"])
            )
        ]

    elif size_category == "medium":
        # Medium test file with 100 variables
        variables = {}
        equations = []

        for i in range(100):
            variables[f"x_{i}"] = ModelVariable(type="state", units="mol/L", default=1e-6)
            variables[f"k_{i}"] = ModelVariable(type="parameter", units="1/s", default=0.01)

            equations.append(Equation(
                lhs=ExprNode(op="D", args=[f"x_{i}"], wrt="t"),
                rhs=ExprNode(op="*", args=[ExprNode(op="-", args=[f"k_{i}"]), f"x_{i}"])
            ))

    elif size_category == "large":
        # Large test file with 1000 variables and complex expressions
        variables = {}
        equations = []

        for i in range(1000):
            variables[f"species_{i}"] = ModelVariable(type="state", units="mol/L", default=1e-12)
            variables[f"rate_{i}"] = ModelVariable(type="parameter", units="cm3/molecule/s", default=1e-13)
            variables[f"temp_factor_{i}"] = ModelVariable(type="parameter", units="1", default=1.0)

            # Complex kinetic expression
            complex_rhs = ExprNode(op="+", args=[
                ExprNode(op="*", args=[f"rate_{i}", f"species_{i}", "temperature"]),
                ExprNode(op="*", args=[
                    f"temp_factor_{i}",
                    ExprNode(op="exp", args=[
                        ExprNode(op="/", args=[-1000.0, "temperature"])
                    ])
                ])
            ])

            equations.append(Equation(
                lhs=ExprNode(op="D", args=[f"species_{i}"], wrt="t"),
                rhs=complex_rhs
            ))

        # Add common variables
        variables["temperature"] = ModelVariable(type="parameter", units="K", default=298.15)

    else:
        raise ValueError(f"Unknown size category: {size_category}")

    return EsmFile(
        version="0.1.0",
        metadata=Metadata(
            title=f"Memory Test Model ({size_category})",
            description=f"Generated for memory profiling - {size_category} size"
        ),
        models=[Model(
            name=f"{size_category}_test_model",
            variables=variables,
            equations=equations
        )]
    )


def profile_parse_operation(profiler: MemoryProfiler, json_data: str, iterations: int = 10) -> Dict[str, Any]:
    """Profile ESM parsing operation."""
    if not ESM_FORMAT_AVAILABLE:
        return {'error': 'ESM format not available'}

    results = {
        'operation': 'parse',
        'iterations': iterations,
        'file_size_mb': len(json_data.encode('utf-8')) / 1024 / 1024
    }

    # Take initial snapshot
    start_snapshot = profiler.take_snapshot("parse_start")

    # Perform repeated parsing to amplify memory effects
    parsed_objects = []
    for i in range(iterations):
        try:
            esm_obj = load(json_data)
            parsed_objects.append(esm_obj)

            if i % max(1, iterations // 5) == 0:  # Take snapshots at intervals
                profiler.take_snapshot(f"parse_iteration_{i}")
        except Exception as e:
            results['error'] = str(e)
            return results

    # Take final snapshot
    end_snapshot = profiler.take_snapshot("parse_end")

    # Force garbage collection and take another snapshot
    gc.collect()
    gc_snapshot = profiler.take_snapshot("parse_after_gc")

    # Calculate memory metrics
    parse_delta = profiler.get_memory_delta(start_snapshot, end_snapshot)
    gc_delta = profiler.get_memory_delta(end_snapshot, gc_snapshot)

    results.update({
        'memory_per_parse_mb': parse_delta['rss_delta_mb'] / iterations if iterations > 0 else 0,
        'total_memory_delta_mb': parse_delta['rss_delta_mb'],
        'memory_recovered_by_gc_mb': abs(gc_delta['rss_delta_mb']),
        'python_memory_delta_mb': parse_delta['python_delta_mb'],
        'gc_objects_created': parse_delta['gc_objects_delta'],
        'parse_time_per_iteration_s': parse_delta['duration_s'] / iterations if iterations > 0 else 0,
        'objects_parsed': len(parsed_objects)
    })

    # Clean up
    del parsed_objects
    gc.collect()

    return results


def profile_serialize_operation(profiler: MemoryProfiler, esm_obj: EsmFile, iterations: int = 10) -> Dict[str, Any]:
    """Profile ESM serialization operation."""
    if not ESM_FORMAT_AVAILABLE:
        return {'error': 'ESM format not available'}

    results = {
        'operation': 'serialize',
        'iterations': iterations
    }

    # Take initial snapshot
    start_snapshot = profiler.take_snapshot("serialize_start")

    # Perform repeated serialization
    serialized_strings = []
    for i in range(iterations):
        try:
            json_str = save(esm_obj)
            serialized_strings.append(json_str)

            if i % max(1, iterations // 5) == 0:
                profiler.take_snapshot(f"serialize_iteration_{i}")
        except Exception as e:
            results['error'] = str(e)
            return results

    # Take final snapshot
    end_snapshot = profiler.take_snapshot("serialize_end")

    # Force garbage collection
    gc.collect()
    gc_snapshot = profiler.take_snapshot("serialize_after_gc")

    # Calculate metrics
    serialize_delta = profiler.get_memory_delta(start_snapshot, end_snapshot)
    gc_delta = profiler.get_memory_delta(end_snapshot, gc_snapshot)

    # Get average output size
    avg_output_size_mb = sum(len(s.encode('utf-8')) for s in serialized_strings) / len(serialized_strings) / 1024 / 1024

    results.update({
        'memory_per_serialize_mb': serialize_delta['rss_delta_mb'] / iterations if iterations > 0 else 0,
        'total_memory_delta_mb': serialize_delta['rss_delta_mb'],
        'memory_recovered_by_gc_mb': abs(gc_delta['rss_delta_mb']),
        'python_memory_delta_mb': serialize_delta['python_delta_mb'],
        'serialize_time_per_iteration_s': serialize_delta['duration_s'] / iterations if iterations > 0 else 0,
        'avg_output_size_mb': avg_output_size_mb,
        'strings_generated': len(serialized_strings)
    })

    # Clean up
    del serialized_strings
    gc.collect()

    return results


def run_memory_leak_test(profiler: MemoryProfiler, size_category: str, iterations: int = 100) -> Dict[str, Any]:
    """Run memory leak detection test."""
    results = {
        'test': 'memory_leak_detection',
        'size_category': size_category,
        'iterations': iterations
    }

    if not ESM_FORMAT_AVAILABLE:
        results['error'] = 'ESM format not available'
        return results

    # Create test data
    try:
        esm_obj = create_test_esm_file(size_category)
        if not esm_obj:
            results['error'] = 'Failed to create test ESM file'
            return results

        json_str = save(esm_obj)
    except Exception as e:
        results['error'] = f'Failed to create test data: {e}'
        return results

    # Take initial snapshot
    start_snapshot = profiler.take_snapshot("leak_test_start")

    # Perform repeated load-modify-save cycles
    for i in range(iterations):
        try:
            # Load
            loaded_esm = load(json_str)

            # Modify (add a small change to force new memory allocation)
            loaded_esm.metadata.description = f"Modified iteration {i}"

            # Save
            new_json = save(loaded_esm)

            # Force some cleanup periodically
            if i % 20 == 0:
                profiler.take_snapshot(f"leak_test_iter_{i}")
                gc.collect()

            del loaded_esm, new_json

        except Exception as e:
            results['error'] = f'Error in iteration {i}: {e}'
            break

    # Final cleanup and snapshot
    gc.collect()
    end_snapshot = profiler.take_snapshot("leak_test_end")

    # Analyze for leaks
    leaks = profiler.detect_memory_leaks(threshold_mb=1.0)  # Lower threshold for leak tests

    final_delta = profiler.get_memory_delta(start_snapshot, end_snapshot)

    results.update({
        'total_memory_delta_mb': final_delta['rss_delta_mb'],
        'memory_per_iteration_mb': final_delta['rss_delta_mb'] / iterations if iterations > 0 else 0,
        'potential_leaks_detected': len(leaks),
        'leak_details': leaks,
        'test_completed_successfully': 'error' not in results
    })

    return results


def main():
    """Main memory profiling function."""
    parser = argparse.ArgumentParser(description='Memory profiling for ESM format operations')
    parser.add_argument('--size', choices=['small', 'medium', 'large'], default='medium',
                       help='Size of test data to generate')
    parser.add_argument('--iterations', type=int, default=50,
                       help='Number of iterations for each test')
    parser.add_argument('--output', type=str, default='memory_profile_results.json',
                       help='Output file for results')
    parser.add_argument('--enable-tracemalloc', action='store_true', default=True,
                       help='Enable Python tracemalloc for detailed memory tracking')
    parser.add_argument('--leak-test-only', action='store_true',
                       help='Run only memory leak detection tests')

    args = parser.parse_args()

    # Initialize profiler
    profiler = MemoryProfiler(enable_tracemalloc=args.enable_tracemalloc)

    print(f"Starting memory profiling with {args.size} test data...")
    print(f"Iterations: {args.iterations}")
    print(f"Python tracemalloc: {'enabled' if args.enable_tracemalloc else 'disabled'}")
    print(f"ESM format available: {ESM_FORMAT_AVAILABLE}")
    print()

    all_results = {
        'config': {
            'size_category': args.size,
            'iterations': args.iterations,
            'tracemalloc_enabled': args.enable_tracemalloc,
            'esm_format_available': ESM_FORMAT_AVAILABLE
        },
        'tests': {}
    }

    if not ESM_FORMAT_AVAILABLE:
        print("Error: ESM format library not available. Cannot run memory profiling.")
        all_results['error'] = 'ESM format library not available'
    else:
        # Create test data
        try:
            esm_obj = create_test_esm_file(args.size)
            json_str = save(esm_obj)
            print(f"Created {args.size} test ESM file: {len(json_str.encode('utf-8')) / 1024 / 1024:.2f}MB")
        except Exception as e:
            print(f"Error creating test data: {e}")
            all_results['error'] = f'Failed to create test data: {e}'
            esm_obj = None
            json_str = None

        if esm_obj and json_str:
            if not args.leak_test_only:
                # Run parse profiling
                print("\nRunning parse operation profiling...")
                parse_results = profile_parse_operation(profiler, json_str, args.iterations)
                all_results['tests']['parse'] = parse_results

                if 'error' not in parse_results:
                    print(f"Parse memory per operation: {parse_results['memory_per_parse_mb']:.3f}MB")
                    print(f"Parse time per operation: {parse_results['parse_time_per_iteration_s']*1000:.2f}ms")

                # Run serialize profiling
                print("\nRunning serialize operation profiling...")
                serialize_results = profile_serialize_operation(profiler, esm_obj, args.iterations)
                all_results['tests']['serialize'] = serialize_results

                if 'error' not in serialize_results:
                    print(f"Serialize memory per operation: {serialize_results['memory_per_serialize_mb']:.3f}MB")
                    print(f"Serialize time per operation: {serialize_results['serialize_time_per_iteration_s']*1000:.2f}ms")

            # Run memory leak test
            print("\nRunning memory leak detection test...")
            leak_results = run_memory_leak_test(profiler, args.size, args.iterations * 2)  # More iterations for leak detection
            all_results['tests']['leak_detection'] = leak_results

            if leak_results.get('potential_leaks_detected', 0) > 0:
                print(f"⚠️  Potential memory leaks detected: {leak_results['potential_leaks_detected']}")
            else:
                print("✅ No significant memory leaks detected")

            print(f"Memory per leak-test iteration: {leak_results.get('memory_per_iteration_mb', 0):.4f}MB")

    # Generate profiler report
    print("\nGenerating memory profiler report...")
    profiler_report = profiler.generate_report()
    all_results['profiler_report'] = profiler_report

    # Display summary
    if profiler_report.get('summary'):
        summary = profiler_report['summary']
        print(f"\nMemory Profile Summary:")
        print(f"  Duration: {summary['total_duration_s']:.2f}s")
        print(f"  Peak RSS: {summary['peak_rss_mb']:.1f}MB")
        print(f"  Total memory delta: {summary['total_rss_delta_mb']:.1f}MB")
        if summary.get('peak_python_mb'):
            print(f"  Peak Python memory: {summary['peak_python_mb']:.1f}MB")

        if profiler_report['leak_detection']['potential_leaks_found'] > 0:
            print(f"  ⚠️  Potential memory leaks: {profiler_report['leak_detection']['potential_leaks_found']}")
        else:
            print("  ✅ No memory leaks detected")

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\nMemory profiling results saved to: {output_path}")

    # Return appropriate exit code
    if all_results.get('error') or any(
        'error' in test_result for test_result in all_results.get('tests', {}).values()
        if isinstance(test_result, dict)
    ):
        return 1

    return 0


if __name__ == '__main__':
    exit(main())