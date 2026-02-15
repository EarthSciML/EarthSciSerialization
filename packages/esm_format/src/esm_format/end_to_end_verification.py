"""
End-to-end atmospheric chemistry simulation verification.

This module implements the complete simulation tier with comprehensive
atmospheric chemistry verification as specified in the task requirements.
It demonstrates end-to-end workflow from ESM file to numerical solution
with Julia MTK/Catalyst integration and Python SciPy backends.
"""

import os
import sys
import json
import time
import traceback
from typing import Dict, List, Tuple, Optional, Any, Union
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# ESM Format imports
from .atmospheric_verification import (
    AtmosphericChemistryVerifier, AtmosphericChemistryScenario,
    run_atmospheric_chemistry_verification_suite
)
from .julia_integration import (
    JuliaIntegrator, JuliaSimulationConfig, compare_python_julia_performance
)
from .simulation import simulate, SimulationResult
from .parse import load
from .serialize import save
from .types import EsmFile, Metadata


class EndToEndVerificationSuite:
    """Complete end-to-end verification suite for atmospheric chemistry."""

    def __init__(self, output_dir: str = "verification_results"):
        """Initialize verification suite."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.verifier = AtmosphericChemistryVerifier()
        self.julia_integrator = JuliaIntegrator()

        # Results storage
        self.python_results = {}
        self.julia_results = {}
        self.comparison_results = {}
        self.performance_benchmarks = {}

        # Generate timestamp for this run
        self.run_timestamp = time.strftime("%Y%m%d_%H%M%S")

    def run_complete_verification(self, scenarios: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run complete end-to-end verification suite.

        Args:
            scenarios: List of scenario names to run (None for all)

        Returns:
            Complete verification results
        """
        print("=" * 80)
        print("ATMOSPHERIC CHEMISTRY SIMULATION VERIFICATION")
        print("=" * 80)
        print(f"Run timestamp: {self.run_timestamp}")
        print(f"Output directory: {self.output_dir}")
        print(f"Python backend: Available")
        print(f"Julia backend: {'Available' if self.julia_integrator.is_available() else 'Not available'}")
        print()

        # Step 1: Python SciPy verification
        print("Step 1: Python SciPy Backend Verification")
        print("-" * 50)
        self.python_results = self._run_python_verification(scenarios)
        self._save_results("python_results.json", self.python_results)

        # Step 2: Julia MTK/Catalyst verification (if available)
        if self.julia_integrator.is_available():
            print("\nStep 2: Julia MTK/Catalyst Backend Verification")
            print("-" * 50)
            self.julia_results = self._run_julia_verification(scenarios)
            self._save_results("julia_results.json", self.julia_results)

            # Step 3: Cross-backend comparison
            print("\nStep 3: Cross-Backend Comparison")
            print("-" * 50)
            self.comparison_results = self._run_backend_comparison(scenarios)
            self._save_results("comparison_results.json", self.comparison_results)

            # Step 4: Performance benchmarking
            print("\nStep 4: Performance Benchmarking")
            print("-" * 50)
            self.performance_benchmarks = self._run_performance_benchmarks(scenarios)
            self._save_results("performance_benchmarks.json", self.performance_benchmarks)
        else:
            print("\nStep 2-4: Skipped (Julia backend not available)")

        # Step 5: Generate comprehensive reports
        print("\nStep 5: Report Generation")
        print("-" * 50)
        final_report = self._generate_final_report()

        print(f"\nVerification completed. Results saved to {self.output_dir}")
        return final_report

    def _run_python_verification(self, scenarios: Optional[List[str]]) -> Dict[str, Any]:
        """Run Python SciPy backend verification."""
        results = {}

        # Run standard atmospheric chemistry scenarios
        print("Running atmospheric chemistry scenarios...")
        scenario_results = run_atmospheric_chemistry_verification_suite()

        for scenario_name, result in scenario_results.items():
            if scenarios is None or scenario_name in scenarios:
                print(f"  {scenario_name}: {'PASSED' if result.success else 'FAILED'}")
                if result.runtime > 0:
                    print(f"    Runtime: {result.runtime:.3f}s")
                    print(f"    Function evaluations: {result.simulation_result.nfev if result.simulation_result else 0}")

        results['scenarios'] = scenario_results

        # Test ESM file roundtrip capability
        print("Testing ESM file roundtrip...")
        roundtrip_results = self._test_esm_roundtrip()
        results['esm_roundtrip'] = roundtrip_results
        print(f"  ESM roundtrip: {'PASSED' if roundtrip_results['success'] else 'FAILED'}")

        # Test numerical stability
        print("Testing numerical stability...")
        stability_results = self._test_numerical_stability()
        results['numerical_stability'] = stability_results
        print(f"  Numerical stability: {'PASSED' if stability_results['all_stable'] else 'FAILED'}")

        return results

    def _run_julia_verification(self, scenarios: Optional[List[str]]) -> Dict[str, Any]:
        """Run Julia MTK/Catalyst backend verification."""
        results = {}

        if not self.julia_integrator.is_available():
            return {'error': 'Julia integration not available'}

        # Test Julia backend with atmospheric chemistry scenarios
        scenario_results = {}
        for scenario_name in self.verifier.scenarios.keys():
            if scenarios is None or scenario_name in scenarios:
                try:
                    scenario = self.verifier.scenarios[scenario_name]
                    print(f"Running {scenario_name} with Julia backend...")

                    julia_result, julia_perf = self.julia_integrator.simulate_reaction_system(
                        scenario.reaction_system,
                        scenario.initial_conditions,
                        scenario.time_span
                    )

                    scenario_results[scenario_name] = {
                        'success': julia_result.success,
                        'message': julia_result.message,
                        'runtime': julia_perf.total_time,
                        'nfev': julia_perf.nfev,
                        'memory_usage': julia_perf.memory_usage,
                        'final_time': julia_result.t[-1] if julia_result.success else None,
                        'n_timepoints': len(julia_result.t) if julia_result.success else 0
                    }

                    print(f"  {scenario_name}: {'PASSED' if julia_result.success else 'FAILED'}")
                    if julia_result.success:
                        print(f"    Runtime: {julia_perf.total_time:.3f}s")
                        print(f"    Memory: {julia_perf.memory_usage:.1f} MB")

                except Exception as e:
                    scenario_results[scenario_name] = {
                        'success': False,
                        'error': str(e),
                        'error_type': type(e).__name__
                    }
                    print(f"  {scenario_name}: FAILED ({type(e).__name__})")

        results['scenarios'] = scenario_results

        # Test solver benchmarking
        print("Benchmarking Julia solvers...")
        solver_benchmark = self._benchmark_julia_solvers()
        results['solver_benchmark'] = solver_benchmark

        return results

    def _run_backend_comparison(self, scenarios: Optional[List[str]]) -> Dict[str, Any]:
        """Compare Python and Julia backend results."""
        comparison_results = {}

        for scenario_name in self.verifier.scenarios.keys():
            if scenarios is None or scenario_name in scenarios:
                try:
                    scenario = self.verifier.scenarios[scenario_name]
                    print(f"Comparing backends for {scenario_name}...")

                    # Get Python result from previous run
                    python_result = None
                    if (scenario_name in self.python_results.get('scenarios', {}) and
                        self.python_results['scenarios'][scenario_name].simulation_result):
                        python_result = self.python_results['scenarios'][scenario_name].simulation_result

                    if python_result is None:
                        # Run Python simulation if not available
                        python_result = simulate(
                            scenario.reaction_system,
                            scenario.initial_conditions,
                            scenario.time_span
                        )

                    # Compare with Julia
                    comparison = self.julia_integrator.compare_with_scipy(
                        scenario.reaction_system,
                        scenario.initial_conditions,
                        scenario.time_span,
                        python_result
                    )

                    comparison_results[scenario_name] = comparison
                    print(f"  {scenario_name}: {'Agreement' if comparison.get('solutions_agree', False) else 'Disagreement'}")
                    if 'max_relative_error' in comparison:
                        print(f"    Max error: {comparison['max_relative_error']:.2e}")

                except Exception as e:
                    comparison_results[scenario_name] = {
                        'error': str(e),
                        'error_type': type(e).__name__
                    }
                    print(f"  {scenario_name}: FAILED ({type(e).__name__})")

        return comparison_results

    def _run_performance_benchmarks(self, scenarios: Optional[List[str]]) -> Dict[str, Any]:
        """Run performance benchmarks."""
        benchmarks = {}

        # Benchmark different problem sizes
        problem_sizes = ['small', 'medium', 'large']

        for size in problem_sizes:
            print(f"Benchmarking {size} problems...")
            size_benchmarks = {}

            # Use ozone_nox_cycle as base problem and scale complexity
            base_scenario = self.verifier.scenarios['ozone_nox_cycle']

            # Scale the problem (simplified - would normally add more species/reactions)
            time_scales = {'small': 3600, 'medium': 12*3600, 'large': 24*3600}
            time_span = (0, time_scales[size])

            # Python benchmark
            try:
                start_time = time.time()
                python_result = simulate(
                    base_scenario.reaction_system,
                    base_scenario.initial_conditions,
                    time_span,
                    rtol=1e-6, atol=1e-8
                )
                python_time = time.time() - start_time

                size_benchmarks['python'] = {
                    'success': python_result.success,
                    'runtime': python_time,
                    'nfev': python_result.nfev,
                    'timepoints': len(python_result.t) if python_result.success else 0
                }
            except Exception as e:
                size_benchmarks['python'] = {'error': str(e)}

            # Julia benchmark
            if self.julia_integrator.is_available():
                try:
                    julia_result, julia_perf = self.julia_integrator.simulate_reaction_system(
                        base_scenario.reaction_system,
                        base_scenario.initial_conditions,
                        time_span
                    )

                    size_benchmarks['julia'] = {
                        'success': julia_result.success,
                        'runtime': julia_perf.total_time,
                        'compile_time': julia_perf.compile_time,
                        'solve_time': julia_perf.solve_time,
                        'nfev': julia_perf.nfev,
                        'memory_usage': julia_perf.memory_usage,
                        'timepoints': len(julia_result.t) if julia_result.success else 0
                    }
                except Exception as e:
                    size_benchmarks['julia'] = {'error': str(e)}

            benchmarks[size] = size_benchmarks

        return benchmarks

    def _benchmark_julia_solvers(self) -> Dict[str, Any]:
        """Benchmark different Julia ODE solvers."""
        if not self.julia_integrator.is_available():
            return {'error': 'Julia not available'}

        # Use a challenging stiff problem (urban chemistry)
        scenario = self.verifier.scenarios['urban_chemistry']

        try:
            solver_results = self.julia_integrator.benchmark_solvers(
                scenario.reaction_system,
                scenario.initial_conditions,
                (0, 3600),  # 1 hour simulation
                solvers=['Rosenbrock23', 'Rodas5', 'FBDF', 'Tsit5', 'Vern7']
            )

            # Find best solver
            best_solver = min(
                solver_results.keys(),
                key=lambda s: solver_results[s].total_time
                if solver_results[s].total_time != float('inf') else float('inf')
            )

            return {
                'solver_results': {
                    solver: {
                        'total_time': perf.total_time,
                        'solve_time': perf.solve_time,
                        'nfev': perf.nfev,
                        'memory_usage': perf.memory_usage
                    }
                    for solver, perf in solver_results.items()
                },
                'best_solver': best_solver,
                'best_time': solver_results[best_solver].total_time
            }
        except Exception as e:
            return {'error': str(e)}

    def _test_esm_roundtrip(self) -> Dict[str, Any]:
        """Test ESM file serialization roundtrip."""
        try:
            # Create test ESM file from a scenario
            scenario = self.verifier.scenarios['ozone_nox_cycle']

            # Convert to ESM file
            esm_file = EsmFile(
                version="0.1.0",
                metadata=Metadata(
                    title="Test atmospheric chemistry model",
                    description="Generated for roundtrip testing",
                    created=time.strftime("%Y-%m-%dT%H:%M:%SZ")
                ),
                reaction_systems=[scenario.reaction_system]
            )

            # Serialize to JSON
            json_str = save(esm_file)

            # Deserialize back
            reconstructed = load(json_str)

            # Verify reconstruction
            success = (
                len(reconstructed.reaction_systems) == 1 and
                reconstructed.reaction_systems[0].name == scenario.reaction_system.name and
                len(reconstructed.reaction_systems[0].species) == len(scenario.reaction_system.species) and
                len(reconstructed.reaction_systems[0].reactions) == len(scenario.reaction_system.reactions)
            )

            # Save test file
            test_file_path = self.output_dir / "test_roundtrip.esm"
            with open(test_file_path, 'w') as f:
                f.write(json_str)

            return {
                'success': success,
                'original_species_count': len(scenario.reaction_system.species),
                'reconstructed_species_count': len(reconstructed.reaction_systems[0].species),
                'original_reaction_count': len(scenario.reaction_system.reactions),
                'reconstructed_reaction_count': len(reconstructed.reaction_systems[0].reactions),
                'file_size_bytes': len(json_str),
                'test_file_path': str(test_file_path)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }

    def _test_numerical_stability(self) -> Dict[str, Any]:
        """Test numerical stability across different tolerances."""
        results = {'all_stable': True, 'tolerance_tests': {}}

        # Test with different tolerance levels
        tolerances = [
            {'rtol': 1e-4, 'atol': 1e-6},
            {'rtol': 1e-6, 'atol': 1e-8},
            {'rtol': 1e-8, 'atol': 1e-10}
        ]

        scenario = self.verifier.scenarios['ozone_nox_cycle']

        reference_result = None
        for i, tol in enumerate(tolerances):
            tol_name = f"tol_{i+1}"
            try:
                result = simulate(
                    scenario.reaction_system,
                    scenario.initial_conditions,
                    scenario.time_span,
                    **tol
                )

                test_result = {
                    'success': result.success,
                    'nfev': result.nfev,
                    'final_time': result.t[-1] if result.success else None,
                    'tolerance': tol
                }

                if result.success:
                    if reference_result is not None:
                        # Compare with reference (first successful result)
                        # Interpolate to common time points
                        common_times = np.linspace(scenario.time_span[0], scenario.time_span[1], 50)
                        ref_interp = np.zeros((reference_result.y.shape[0], len(common_times)))
                        curr_interp = np.zeros((result.y.shape[0], len(common_times)))

                        for j in range(reference_result.y.shape[0]):
                            ref_interp[j, :] = np.interp(common_times, reference_result.t, reference_result.y[j, :])
                            curr_interp[j, :] = np.interp(common_times, result.t, result.y[j, :])

                        # Calculate relative difference
                        rel_diff = np.abs(ref_interp - curr_interp) / (np.abs(ref_interp) + 1e-16)
                        max_rel_diff = np.max(rel_diff)

                        test_result['max_relative_difference'] = float(max_rel_diff)
                        test_result['stable'] = max_rel_diff < 0.01  # 1% stability criterion

                        if not test_result['stable']:
                            results['all_stable'] = False
                    else:
                        reference_result = result
                        test_result['stable'] = True
                else:
                    test_result['stable'] = False
                    results['all_stable'] = False

                results['tolerance_tests'][tol_name] = test_result

            except Exception as e:
                results['tolerance_tests'][tol_name] = {
                    'success': False,
                    'error': str(e),
                    'stable': False
                }
                results['all_stable'] = False

        return results

    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final report."""
        report = {
            'verification_summary': self._create_verification_summary(),
            'performance_summary': self._create_performance_summary(),
            'recommendations': self._create_recommendations(),
            'detailed_results': {
                'python_results': self.python_results,
                'julia_results': self.julia_results,
                'comparison_results': self.comparison_results,
                'performance_benchmarks': self.performance_benchmarks
            }
        }

        # Save comprehensive report
        report_file = self.output_dir / f"comprehensive_report_{self.run_timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Generate summary report
        summary_report = self._generate_summary_report(report)
        summary_file = self.output_dir / f"summary_report_{self.run_timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write(summary_report)

        print(f"Final report saved to {report_file}")
        print(f"Summary report saved to {summary_file}")

        return report

    def _create_verification_summary(self) -> Dict[str, Any]:
        """Create verification summary."""
        summary = {}

        # Python verification summary
        if self.python_results:
            python_scenarios = self.python_results.get('scenarios', {})
            python_passed = sum(1 for r in python_scenarios.values() if r.success)
            python_total = len(python_scenarios)

            summary['python_verification'] = {
                'total_scenarios': python_total,
                'passed_scenarios': python_passed,
                'success_rate': python_passed / python_total if python_total > 0 else 0,
                'esm_roundtrip_success': self.python_results.get('esm_roundtrip', {}).get('success', False),
                'numerical_stability': self.python_results.get('numerical_stability', {}).get('all_stable', False)
            }

        # Julia verification summary
        if self.julia_results and 'scenarios' in self.julia_results:
            julia_scenarios = self.julia_results['scenarios']
            julia_passed = sum(1 for r in julia_scenarios.values() if r.get('success', False))
            julia_total = len(julia_scenarios)

            summary['julia_verification'] = {
                'total_scenarios': julia_total,
                'passed_scenarios': julia_passed,
                'success_rate': julia_passed / julia_total if julia_total > 0 else 0,
                'available': True
            }
        else:
            summary['julia_verification'] = {'available': False}

        # Cross-backend comparison summary
        if self.comparison_results:
            agreements = sum(1 for r in self.comparison_results.values()
                           if r.get('solutions_agree', False))
            total_comparisons = len(self.comparison_results)

            summary['backend_comparison'] = {
                'total_comparisons': total_comparisons,
                'agreements': agreements,
                'agreement_rate': agreements / total_comparisons if total_comparisons > 0 else 0
            }

        return summary

    def _create_performance_summary(self) -> Dict[str, Any]:
        """Create performance summary."""
        summary = {}

        if self.performance_benchmarks:
            # Analyze performance trends
            python_times = []
            julia_times = []

            for size, benchmarks in self.performance_benchmarks.items():
                if 'python' in benchmarks and 'runtime' in benchmarks['python']:
                    python_times.append(benchmarks['python']['runtime'])

                if 'julia' in benchmarks and 'runtime' in benchmarks['julia']:
                    julia_times.append(benchmarks['julia']['runtime'])

            summary['performance_trends'] = {
                'python_times': python_times,
                'julia_times': julia_times,
                'julia_faster': np.mean(julia_times) < np.mean(python_times) if julia_times and python_times else None
            }

        # Julia solver benchmarks
        if self.julia_results and 'solver_benchmark' in self.julia_results:
            solver_bench = self.julia_results['solver_benchmark']
            if 'best_solver' in solver_bench:
                summary['best_julia_solver'] = {
                    'name': solver_bench['best_solver'],
                    'time': solver_bench['best_time']
                }

        return summary

    def _create_recommendations(self) -> List[str]:
        """Create recommendations based on verification results."""
        recommendations = []

        # Python verification recommendations
        if self.python_results:
            python_scenarios = self.python_results.get('scenarios', {})
            failed_scenarios = [name for name, result in python_scenarios.items() if not result.success]

            if failed_scenarios:
                recommendations.append(
                    f"Python verification failed for scenarios: {', '.join(failed_scenarios)}. "
                    "Review numerical tolerances and solver settings."
                )

            if not self.python_results.get('numerical_stability', {}).get('all_stable', True):
                recommendations.append(
                    "Numerical stability issues detected. Consider using stricter tolerances "
                    "for production simulations."
                )

        # Julia recommendations
        if self.julia_integrator.is_available():
            if self.julia_results and 'solver_benchmark' in self.julia_results:
                best_solver = self.julia_results['solver_benchmark'].get('best_solver')
                if best_solver:
                    recommendations.append(
                        f"For Julia simulations, {best_solver} shows best performance for these problems."
                    )
        else:
            recommendations.append(
                "Julia integration not available. Install Julia and ESMFormat.jl for enhanced performance."
            )

        # Backend comparison recommendations
        if self.comparison_results:
            disagreements = [name for name, result in self.comparison_results.items()
                           if not result.get('solutions_agree', True)]
            if disagreements:
                recommendations.append(
                    f"Backend disagreements found in: {', '.join(disagreements)}. "
                    "Review solver tolerances and numerical methods."
                )

        return recommendations

    def _generate_summary_report(self, report: Dict[str, Any]) -> str:
        """Generate human-readable summary report."""
        lines = []
        lines.append("=" * 80)
        lines.append("ATMOSPHERIC CHEMISTRY SIMULATION VERIFICATION SUMMARY")
        lines.append("=" * 80)
        lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Verification summary
        if 'verification_summary' in report:
            vs = report['verification_summary']
            lines.append("VERIFICATION RESULTS")
            lines.append("-" * 30)

            if 'python_verification' in vs:
                pv = vs['python_verification']
                lines.append(f"Python SciPy Backend: {pv['passed_scenarios']}/{pv['total_scenarios']} scenarios passed ({pv['success_rate']:.1%})")
                lines.append(f"  ESM Roundtrip: {'PASSED' if pv['esm_roundtrip_success'] else 'FAILED'}")
                lines.append(f"  Numerical Stability: {'PASSED' if pv['numerical_stability'] else 'FAILED'}")

            if 'julia_verification' in vs:
                jv = vs['julia_verification']
                if jv['available']:
                    lines.append(f"Julia MTK/Catalyst Backend: {jv['passed_scenarios']}/{jv['total_scenarios']} scenarios passed ({jv['success_rate']:.1%})")
                else:
                    lines.append("Julia MTK/Catalyst Backend: Not available")

            if 'backend_comparison' in vs:
                bc = vs['backend_comparison']
                lines.append(f"Backend Agreement: {bc['agreements']}/{bc['total_comparisons']} comparisons agreed ({bc['agreement_rate']:.1%})")

        lines.append("")

        # Performance summary
        if 'performance_summary' in report:
            ps = report['performance_summary']
            lines.append("PERFORMANCE RESULTS")
            lines.append("-" * 30)

            if 'best_julia_solver' in ps:
                bjs = ps['best_julia_solver']
                lines.append(f"Best Julia Solver: {bjs['name']} ({bjs['time']:.3f}s)")

            if 'performance_trends' in ps:
                pt = ps['performance_trends']
                if pt['julia_faster'] is not None:
                    faster_backend = "Julia" if pt['julia_faster'] else "Python"
                    lines.append(f"Faster Backend: {faster_backend}")

        lines.append("")

        # Recommendations
        if 'recommendations' in report:
            lines.append("RECOMMENDATIONS")
            lines.append("-" * 30)
            for i, rec in enumerate(report['recommendations'], 1):
                lines.append(f"{i}. {rec}")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def _save_results(self, filename: str, data: Any):
        """Save results to JSON file."""
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)


# Main execution function
def run_end_to_end_verification(
    output_dir: str = "verification_results",
    scenarios: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Run complete end-to-end atmospheric chemistry verification.

    Args:
        output_dir: Directory to save results
        scenarios: List of scenarios to run (None for all)

    Returns:
        Complete verification results
    """
    suite = EndToEndVerificationSuite(output_dir)
    return suite.run_complete_verification(scenarios)


# Command line interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="End-to-end atmospheric chemistry verification")
    parser.add_argument("--output-dir", "-o", default="verification_results",
                       help="Output directory for results")
    parser.add_argument("--scenarios", "-s", nargs="*",
                       help="Specific scenarios to run (default: all)")
    parser.add_argument("--quick", "-q", action="store_true",
                       help="Run quick verification (ozone_nox_cycle only)")

    args = parser.parse_args()

    if args.quick:
        scenarios = ['ozone_nox_cycle']
    else:
        scenarios = args.scenarios

    try:
        results = run_end_to_end_verification(args.output_dir, scenarios)
        print("\nVerification completed successfully!")

        # Print summary to console
        if 'verification_summary' in results:
            vs = results['verification_summary']
            if 'python_verification' in vs:
                pv = vs['python_verification']
                print(f"Python: {pv['passed_scenarios']}/{pv['total_scenarios']} passed")

            if 'julia_verification' in vs and vs['julia_verification']['available']:
                jv = vs['julia_verification']
                print(f"Julia: {jv['passed_scenarios']}/{jv['total_scenarios']} passed")

    except Exception as e:
        print(f"Verification failed with error: {e}")
        traceback.print_exc()
        sys.exit(1)