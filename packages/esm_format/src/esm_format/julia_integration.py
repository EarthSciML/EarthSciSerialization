"""
Julia ModelingToolkit/Catalyst integration for ESM format simulations.

This module provides integration with Julia's ModelingToolkit.jl and Catalyst.jl
packages for high-performance ODE solving and reaction network analysis.
It enables comparison between Python SciPy backend and Julia ODE solvers.
"""

import subprocess
import json
import tempfile
import os
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, asdict
import numpy as np

from .esm_types import ReactionSystem, Model, Species, Parameter, Reaction
from .simulation import SimulationResult


@dataclass
class JuliaSimulationConfig:
    """Configuration for Julia simulation backend."""
    solver: str = "Rosenbrock23"  # Default stiff solver
    abstol: float = 1e-8
    reltol: float = 1e-6
    maxiters: int = 100000
    save_everystep: bool = True
    dense: bool = False
    adaptive: bool = True
    dt: Optional[float] = None
    dtmax: Optional[float] = None
    dtmin: Optional[float] = None
    force_dtmin: bool = False
    threads: int = 1


@dataclass
class JuliaPerformanceMetrics:
    """Performance metrics from Julia simulation."""
    solve_time: float
    compile_time: float
    total_time: float
    memory_usage: float  # MB
    allocations: int
    gc_time: float
    nfev: int
    njev: int
    naccept: int
    nreject: int


class JuliaSimulationError(Exception):
    """Exception raised during Julia simulation."""
    pass


class JuliaIntegrator:
    """Interface for Julia ModelingToolkit/Catalyst integration."""

    def __init__(self, julia_path: str = "julia", esm_julia_path: Optional[str] = None):
        """Initialize Julia integrator.

        Args:
            julia_path: Path to Julia executable
            esm_julia_path: Path to ESMFormat.jl package directory
        """
        self.julia_path = julia_path
        self.esm_julia_path = esm_julia_path or self._find_esm_julia_package()
        self.available = self._check_julia_availability()

        if self.available:
            self._setup_julia_environment()

    def _find_esm_julia_package(self) -> Optional[str]:
        """Find ESMFormat.jl package in the project."""
        # Try relative path from current location
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        julia_pkg_path = os.path.join(project_root, "packages", "ESMFormat.jl")

        if os.path.exists(julia_pkg_path):
            return julia_pkg_path
        return None

    def _check_julia_availability(self) -> bool:
        """Check if Julia is available and ESMFormat.jl can be loaded."""
        try:
            result = subprocess.run(
                [self.julia_path, "--version"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return False

            # Check if ESMFormat.jl is available
            if self.esm_julia_path:
                test_cmd = [
                    self.julia_path,
                    f"--project={self.esm_julia_path}",
                    "-e", "using ESMFormat; println(\"ESMFormat.jl loaded successfully\")"
                ]
                result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=30)
                return result.returncode == 0 and "loaded successfully" in result.stdout

            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _setup_julia_environment(self):
        """Set up Julia environment with required packages."""
        if not self.esm_julia_path:
            return

        try:
            # Instantiate the project environment
            cmd = [
                self.julia_path,
                f"--project={self.esm_julia_path}",
                "-e", "using Pkg; Pkg.instantiate()"
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            pass  # Continue even if instantiation times out

    def is_available(self) -> bool:
        """Check if Julia integration is available."""
        return self.available

    def simulate_reaction_system(
        self,
        reaction_system: ReactionSystem,
        initial_conditions: Dict[str, float],
        time_span: Tuple[float, float],
        config: Optional[JuliaSimulationConfig] = None
    ) -> Tuple[SimulationResult, JuliaPerformanceMetrics]:
        """Simulate reaction system using Julia Catalyst.jl backend.

        Args:
            reaction_system: ESM reaction system
            initial_conditions: Initial concentrations
            time_span: Time span (t_start, t_end)
            config: Julia simulation configuration

        Returns:
            Tuple of (simulation_result, performance_metrics)
        """
        if not self.available:
            raise JuliaSimulationError("Julia integration not available")

        config = config or JuliaSimulationConfig()

        # Create temporary files for data exchange
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as input_file:
            input_data = {
                'reaction_system': self._serialize_reaction_system(reaction_system),
                'initial_conditions': initial_conditions,
                'time_span': list(time_span),
                'config': asdict(config)
            }
            json.dump(input_data, input_file, indent=2)
            input_filename = input_file.name

        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as output_file:
                output_filename = output_file.name

            # Run Julia simulation
            julia_script = f"""
            using ESMFormat
            using JSON
            using OrdinaryDiffEq
            using Catalyst
            using BenchmarkTools

            # Load input data
            input_data = JSON.parsefile("{input_filename}")

            # Convert to Julia structures and simulate
            try
                result_data, perf_data = simulate_esm_reaction_system(input_data)

                # Save results
                output_data = Dict(
                    "success" => true,
                    "result" => result_data,
                    "performance" => perf_data,
                    "message" => "Simulation completed successfully"
                )

                open("{output_filename}", "w") do f
                    JSON.print(f, output_data, 2)
                end
            catch e
                # Save error information
                error_data = Dict(
                    "success" => false,
                    "message" => string(e),
                    "error_type" => string(typeof(e))
                )

                open("{output_filename}", "w") do f
                    JSON.print(f, error_data, 2)
                end
            end
            """

            # Write Julia script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.jl', delete=False) as script_file:
                script_file.write(julia_script)
                script_filename = script_file.name

            # Execute Julia script
            cmd = [
                self.julia_path,
                f"--project={self.esm_julia_path}",
                script_filename
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )

            if result.returncode != 0:
                raise JuliaSimulationError(f"Julia execution failed: {result.stderr}")

            # Load results
            with open(output_filename, 'r') as f:
                output_data = json.load(f)

            if not output_data.get('success', False):
                raise JuliaSimulationError(f"Julia simulation failed: {output_data.get('message', 'Unknown error')}")

            # Parse simulation results
            sim_result = self._parse_simulation_result(output_data['result'])
            perf_metrics = self._parse_performance_metrics(output_data['performance'])

            return sim_result, perf_metrics

        finally:
            # Clean up temporary files
            for filename in [input_filename, output_filename, script_filename]:
                try:
                    os.unlink(filename)
                except FileNotFoundError:
                    pass

    def simulate_ode_system(
        self,
        model: Model,
        initial_conditions: Dict[str, float],
        time_span: Tuple[float, float],
        config: Optional[JuliaSimulationConfig] = None
    ) -> Tuple[SimulationResult, JuliaPerformanceMetrics]:
        """Simulate ODE system using Julia ModelingToolkit.jl backend.

        Args:
            model: ESM model with ODEs
            initial_conditions: Initial values
            time_span: Time span (t_start, t_end)
            config: Julia simulation configuration

        Returns:
            Tuple of (simulation_result, performance_metrics)
        """
        if not self.available:
            raise JuliaSimulationError("Julia integration not available")

        # Similar implementation to simulate_reaction_system but for ODEs
        # This would use MTK instead of Catalyst
        raise NotImplementedError("ODE system simulation not yet implemented")

    def benchmark_solvers(
        self,
        reaction_system: ReactionSystem,
        initial_conditions: Dict[str, float],
        time_span: Tuple[float, float],
        solvers: List[str] = None
    ) -> Dict[str, JuliaPerformanceMetrics]:
        """Benchmark different ODE solvers on the same problem.

        Args:
            reaction_system: ESM reaction system
            initial_conditions: Initial concentrations
            time_span: Time span
            solvers: List of solver names to benchmark

        Returns:
            Dictionary mapping solver names to performance metrics
        """
        if not self.available:
            raise JuliaSimulationError("Julia integration not available")

        solvers = solvers or [
            "Rosenbrock23", "Rodas5", "FBDF", "QNDF",
            "Tsit5", "Vern7", "RadauIIA5", "KenCarp4"
        ]

        results = {}

        for solver in solvers:
            try:
                config = JuliaSimulationConfig(solver=solver)
                _, perf_metrics = self.simulate_reaction_system(
                    reaction_system, initial_conditions, time_span, config
                )
                results[solver] = perf_metrics
            except JuliaSimulationError as e:
                # Some solvers might not be suitable for the problem
                results[solver] = JuliaPerformanceMetrics(
                    solve_time=float('inf'),
                    compile_time=0.0,
                    total_time=float('inf'),
                    memory_usage=0.0,
                    allocations=0,
                    gc_time=0.0,
                    nfev=0, njev=0, naccept=0, nreject=0
                )

        return results

    def compare_with_scipy(
        self,
        reaction_system: ReactionSystem,
        initial_conditions: Dict[str, float],
        time_span: Tuple[float, float],
        scipy_result: SimulationResult
    ) -> Dict[str, Any]:
        """Compare Julia simulation results with SciPy results.

        Args:
            reaction_system: ESM reaction system
            initial_conditions: Initial concentrations
            time_span: Time span
            scipy_result: Results from Python SciPy simulation

        Returns:
            Comparison metrics and analysis
        """
        if not self.available:
            raise JuliaSimulationError("Julia integration not available")

        # Run Julia simulation
        julia_result, julia_perf = self.simulate_reaction_system(
            reaction_system, initial_conditions, time_span
        )

        if not julia_result.success:
            return {
                'comparison_success': False,
                'message': f"Julia simulation failed: {julia_result.message}"
            }

        # Compare results
        comparison = {
            'comparison_success': True,
            'scipy_success': scipy_result.success,
            'julia_success': julia_result.success,
            'scipy_nfev': scipy_result.nfev,
            'julia_nfev': julia_perf.nfev,
            'scipy_solve_time': getattr(scipy_result, 'solve_time', None),
            'julia_solve_time': julia_perf.solve_time,
        }

        if scipy_result.success and julia_result.success:
            # Compare solution accuracy
            # Interpolate to common time points
            common_times = np.linspace(time_span[0], time_span[1], 100)

            # Interpolate both solutions
            scipy_interp = np.zeros((scipy_result.y.shape[0], len(common_times)))
            julia_interp = np.zeros((julia_result.y.shape[0], len(common_times)))

            for i in range(scipy_result.y.shape[0]):
                scipy_interp[i, :] = np.interp(common_times, scipy_result.t, scipy_result.y[i, :])

            for i in range(julia_result.y.shape[0]):
                julia_interp[i, :] = np.interp(common_times, julia_result.t, julia_result.y[i, :])

            # Calculate relative differences
            relative_errors = np.abs(scipy_interp - julia_interp) / (np.abs(scipy_interp) + 1e-16)
            max_relative_error = np.max(relative_errors)
            mean_relative_error = np.mean(relative_errors)

            comparison.update({
                'max_relative_error': float(max_relative_error),
                'mean_relative_error': float(mean_relative_error),
                'solutions_agree': max_relative_error < 1e-3,  # 0.1% tolerance
                'common_time_points': len(common_times),
                'scipy_time_points': len(scipy_result.t),
                'julia_time_points': len(julia_result.t)
            })

        return comparison

    def _serialize_reaction_system(self, reaction_system: ReactionSystem) -> Dict[str, Any]:
        """Serialize reaction system for Julia."""
        return {
            'name': reaction_system.name,
            'species': [
                {
                    'name': spec.name,
                    'formula': getattr(spec, 'formula', spec.name),
                    'units': getattr(spec, 'units', 'mol/mol'),
                    'initial_concentration': getattr(spec, 'initial_concentration', 0.0)
                }
                for spec in reaction_system.species
            ],
            'parameters': [
                {
                    'name': param.name,
                    'value': param.value if hasattr(param, 'value') else param.default,
                    'units': getattr(param, 'units', ''),
                    'description': getattr(param, 'description', '')
                }
                for param in reaction_system.parameters
            ],
            'reactions': [
                {
                    'name': rxn.name,
                    'reactants': dict(rxn.reactants),
                    'products': dict(rxn.products),
                    'rate_constant': self._serialize_expression(rxn.rate_constant),
                    'description': getattr(rxn, 'description', '')
                }
                for rxn in reaction_system.reactions
            ]
        }

    def _serialize_expression(self, expr: Any) -> Union[float, str, Dict]:
        """Serialize expression for Julia."""
        if isinstance(expr, (int, float)):
            return expr
        elif isinstance(expr, str):
            return expr
        elif hasattr(expr, 'op'):  # ExprNode
            return {
                'op': expr.op,
                'args': [self._serialize_expression(arg) for arg in expr.args],
                'wrt': getattr(expr, 'wrt', None)
            }
        else:
            return str(expr)

    def _parse_simulation_result(self, result_data: Dict[str, Any]) -> SimulationResult:
        """Parse simulation result from Julia."""
        return SimulationResult(
            t=np.array(result_data['t']),
            y=np.array(result_data['y']),
            success=result_data['success'],
            message=result_data.get('message', ''),
            nfev=result_data.get('nfev', 0),
            njev=result_data.get('njev', 0),
            nlu=result_data.get('nlu', 0),
            events=result_data.get('events')
        )

    def _parse_performance_metrics(self, perf_data: Dict[str, Any]) -> JuliaPerformanceMetrics:
        """Parse performance metrics from Julia."""
        return JuliaPerformanceMetrics(
            solve_time=perf_data.get('solve_time', 0.0),
            compile_time=perf_data.get('compile_time', 0.0),
            total_time=perf_data.get('total_time', 0.0),
            memory_usage=perf_data.get('memory_usage', 0.0),
            allocations=perf_data.get('allocations', 0),
            gc_time=perf_data.get('gc_time', 0.0),
            nfev=perf_data.get('nfev', 0),
            njev=perf_data.get('njev', 0),
            naccept=perf_data.get('naccept', 0),
            nreject=perf_data.get('nreject', 0)
        )


# Convenience functions
def create_julia_integrator() -> Optional[JuliaIntegrator]:
    """Create Julia integrator if available."""
    integrator = JuliaIntegrator()
    return integrator if integrator.is_available() else None


def compare_python_julia_performance(
    reaction_system: ReactionSystem,
    initial_conditions: Dict[str, float],
    time_span: Tuple[float, float]
) -> Dict[str, Any]:
    """Compare Python and Julia simulation performance."""
    from .simulation import simulate

    results = {
        'python_available': True,
        'julia_available': False,
        'comparison_success': False
    }

    # Run Python simulation
    import time
    start_time = time.time()
    python_result = simulate(reaction_system, initial_conditions, time_span)
    python_time = time.time() - start_time

    results['python_result'] = python_result
    results['python_time'] = python_time

    # Try Julia simulation
    integrator = create_julia_integrator()
    if integrator:
        results['julia_available'] = True
        try:
            julia_result, julia_perf = integrator.simulate_reaction_system(
                reaction_system, initial_conditions, time_span
            )
            results['julia_result'] = julia_result
            results['julia_performance'] = julia_perf

            # Compare
            if python_result.success and julia_result.success:
                comparison = integrator.compare_with_scipy(
                    reaction_system, initial_conditions, time_span, python_result
                )
                results.update(comparison)
        except Exception as e:
            results['julia_error'] = str(e)

    return results