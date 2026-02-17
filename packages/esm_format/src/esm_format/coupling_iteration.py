"""
Coupling iteration and convergence control for ESM Format.

This module implements iterative coupling control for coupled systems, including:
- Convergence checking with multiple criteria
- Iteration limits and early termination
- Relaxation methods for numerical stability
- Convergence acceleration techniques (Aitken, Anderson)

Required for iterative coupling between multiple Earth system components.
"""

# Optional import for numpy - fallback to built-in math if not available
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    import math
    # Create a minimal numpy-like interface for basic operations
    class np_fallback:
        @staticmethod
        def array(data):
            return list(data)

        @staticmethod
        def zeros(shape):
            if isinstance(shape, int):
                return [0.0] * shape
            else:
                return [0.0] * shape[0]

        @staticmethod
        def eye(n):
            result = []
            for i in range(n):
                row = [0.0] * n
                row[i] = 1.0
                result.append(row)
            return result

        @staticmethod
        def mean(data):
            return sum(data) / len(data) if data else 0.0

        @staticmethod
        def sqrt(x):
            return math.sqrt(abs(x))

        @staticmethod
        def append(arr, value):
            return arr + [value]

        class linalg:
            @staticmethod
            def lstsq(A, b, rcond=None):
                # Simplified least squares - just return identity solution
                return [1.0] * len(A[0]), None, None, None

            @staticmethod
            def solve(A, b):
                # Simplified solver - return b (identity matrix assumption)
                return b

            class LinAlgError(Exception):
                pass

    np = np_fallback()
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod

from .esm_types import EsmFile, Model, ReactionSystem
from .coupling_graph import CouplingGraph, construct_coupling_graph


logger = logging.getLogger(__name__)


class ConvergenceMethod(Enum):
    """Convergence checking methods."""
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    RESIDUAL = "residual"
    MIXED = "mixed"


class RelaxationMethod(Enum):
    """Relaxation methods for coupling iteration."""
    NONE = "none"
    FIXED = "fixed"
    ADAPTIVE = "adaptive"
    AITKEN = "aitken"


class AccelerationMethod(Enum):
    """Convergence acceleration methods."""
    NONE = "none"
    AITKEN = "aitken"
    ANDERSON = "anderson"
    SIMPLIFIED_NEWTON = "simplified_newton"


@dataclass
class ConvergenceConfig:
    """Configuration for convergence checking."""
    method: ConvergenceMethod = ConvergenceMethod.MIXED
    absolute_tolerance: float = 1e-6
    relative_tolerance: float = 1e-4
    residual_tolerance: float = 1e-5
    max_iterations: int = 100
    min_iterations: int = 1
    check_variables: Optional[List[str]] = None  # If None, check all coupled variables

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")
        if self.min_iterations < 0:
            raise ValueError("min_iterations must be non-negative")
        if self.min_iterations > self.max_iterations:
            raise ValueError("min_iterations cannot exceed max_iterations")
        if self.absolute_tolerance <= 0:
            raise ValueError("absolute_tolerance must be positive")
        if self.relative_tolerance <= 0:
            raise ValueError("relative_tolerance must be positive")
        if self.residual_tolerance <= 0:
            raise ValueError("residual_tolerance must be positive")


@dataclass
class RelaxationConfig:
    """Configuration for relaxation methods."""
    method: RelaxationMethod = RelaxationMethod.FIXED
    relaxation_factor: float = 0.5
    adaptive_range: Tuple[float, float] = (0.1, 0.9)
    aitken_damping: float = 0.1

    def __post_init__(self):
        """Validate configuration parameters."""
        if not (0 < self.relaxation_factor < 1):
            raise ValueError("relaxation_factor must be between 0 and 1")
        if not (0 < self.adaptive_range[0] < self.adaptive_range[1] < 1):
            raise ValueError("adaptive_range must be (min, max) with 0 < min < max < 1")
        if not (0 < self.aitken_damping < 1):
            raise ValueError("aitken_damping must be between 0 and 1")


@dataclass
class AccelerationConfig:
    """Configuration for convergence acceleration."""
    method: AccelerationMethod = AccelerationMethod.NONE
    anderson_depth: int = 3
    anderson_beta: float = 1.0
    newton_jacobian_update_freq: int = 5

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.anderson_depth < 1:
            raise ValueError("anderson_depth must be at least 1")
        if self.anderson_beta <= 0:
            raise ValueError("anderson_beta must be positive")
        if self.newton_jacobian_update_freq < 1:
            raise ValueError("newton_jacobian_update_freq must be at least 1")


@dataclass
class IterationState:
    """State information for a coupling iteration."""
    iteration: int
    variables: Dict[str, float]
    residuals: Optional[Dict[str, float]] = None
    convergence_metrics: Optional[Dict[str, float]] = None
    relaxation_factor: Optional[float] = None

    def copy(self) -> 'IterationState':
        """Create a deep copy of the iteration state."""
        return IterationState(
            iteration=self.iteration,
            variables=self.variables.copy(),
            residuals=self.residuals.copy() if self.residuals else None,
            convergence_metrics=self.convergence_metrics.copy() if self.convergence_metrics else None,
            relaxation_factor=self.relaxation_factor
        )


@dataclass
class CouplingResult:
    """Result of coupling iteration."""
    converged: bool
    final_state: IterationState
    iteration_history: List[IterationState]
    convergence_reason: str
    total_iterations: int
    execution_time: float = 0.0

    def get_convergence_metrics(self) -> Dict[str, List[float]]:
        """Extract convergence metrics history."""
        metrics = {}
        for state in self.iteration_history:
            if state.convergence_metrics:
                for key, value in state.convergence_metrics.items():
                    if key not in metrics:
                        metrics[key] = []
                    metrics[key].append(value)
        return metrics


class ConvergenceChecker(ABC):
    """Abstract base class for convergence checking algorithms."""

    @abstractmethod
    def check_convergence(
        self,
        current_state: IterationState,
        previous_state: Optional[IterationState],
        config: ConvergenceConfig
    ) -> Tuple[bool, Dict[str, float]]:
        """
        Check if iteration has converged.

        Args:
            current_state: Current iteration state
            previous_state: Previous iteration state (None for first iteration)
            config: Convergence configuration

        Returns:
            Tuple of (converged, convergence_metrics)
        """
        pass


class MixedConvergenceChecker(ConvergenceChecker):
    """Mixed convergence checker using absolute, relative, and residual criteria."""

    def check_convergence(
        self,
        current_state: IterationState,
        previous_state: Optional[IterationState],
        config: ConvergenceConfig
    ) -> Tuple[bool, Dict[str, float]]:
        """Check convergence using mixed criteria."""
        if previous_state is None:
            return False, {}

        metrics = {}
        check_vars = config.check_variables or list(current_state.variables.keys())

        # Absolute convergence check
        max_abs_error = 0.0
        for var in check_vars:
            if var in current_state.variables and var in previous_state.variables:
                abs_error = abs(current_state.variables[var] - previous_state.variables[var])
                max_abs_error = max(max_abs_error, abs_error)

        metrics['max_absolute_error'] = max_abs_error
        abs_converged = max_abs_error < config.absolute_tolerance

        # Relative convergence check
        max_rel_error = 0.0
        for var in check_vars:
            if var in current_state.variables and var in previous_state.variables:
                curr_val = current_state.variables[var]
                prev_val = previous_state.variables[var]
                if abs(prev_val) > 1e-14:  # Avoid division by zero
                    rel_error = abs((curr_val - prev_val) / prev_val)
                    max_rel_error = max(max_rel_error, rel_error)

        metrics['max_relative_error'] = max_rel_error
        rel_converged = max_rel_error < config.relative_tolerance

        # Residual convergence check
        residual_converged = True
        if current_state.residuals:
            max_residual = max(abs(r) for r in current_state.residuals.values())
            metrics['max_residual'] = max_residual
            residual_converged = max_residual < config.residual_tolerance
        else:
            metrics['max_residual'] = 0.0

        # Combined convergence decision based on method
        if config.method == ConvergenceMethod.ABSOLUTE:
            converged = abs_converged
        elif config.method == ConvergenceMethod.RELATIVE:
            converged = rel_converged
        elif config.method == ConvergenceMethod.RESIDUAL:
            converged = residual_converged
        else:  # MIXED
            converged = abs_converged and rel_converged and residual_converged

        return converged, metrics


class RelaxationController:
    """Controls relaxation parameters during coupling iteration."""

    def __init__(self, config: RelaxationConfig):
        self.config = config
        self._history = []

    def compute_relaxation_factor(
        self,
        current_state: IterationState,
        previous_state: Optional[IterationState],
        iteration: int
    ) -> float:
        """Compute relaxation factor for current iteration."""
        if self.config.method == RelaxationMethod.NONE:
            return 1.0

        elif self.config.method == RelaxationMethod.FIXED:
            return self.config.relaxation_factor

        elif self.config.method == RelaxationMethod.ADAPTIVE:
            return self._compute_adaptive_relaxation(current_state, previous_state)

        elif self.config.method == RelaxationMethod.AITKEN:
            return self._compute_aitken_relaxation(current_state, previous_state)

        else:
            raise ValueError(f"Unknown relaxation method: {self.config.method}")

    def _compute_adaptive_relaxation(
        self,
        current_state: IterationState,
        previous_state: Optional[IterationState]
    ) -> float:
        """Compute adaptive relaxation factor based on convergence behavior."""
        if previous_state is None or not current_state.convergence_metrics:
            return self.config.relaxation_factor

        # Simple adaptive strategy: increase relaxation if converging, decrease if diverging
        if len(self._history) < 2:
            self._history.append(current_state.convergence_metrics.get('max_absolute_error', 1.0))
            return self.config.relaxation_factor

        current_error = current_state.convergence_metrics.get('max_absolute_error', 1.0)
        previous_error = self._history[-1]

        self._history.append(current_error)
        if len(self._history) > 10:  # Keep limited history
            self._history.pop(0)

        if current_error < previous_error:
            # Converging - can increase relaxation factor
            new_factor = min(self.config.adaptive_range[1],
                           self.config.relaxation_factor * 1.1)
        else:
            # Diverging - decrease relaxation factor
            new_factor = max(self.config.adaptive_range[0],
                           self.config.relaxation_factor * 0.9)

        self.config.relaxation_factor = new_factor
        return new_factor

    def _compute_aitken_relaxation(
        self,
        current_state: IterationState,
        previous_state: Optional[IterationState]
    ) -> float:
        """Compute Aitken relaxation factor."""
        if previous_state is None or len(self._history) < 2:
            if current_state.variables:
                # Store current variables for next iteration
                self._history.append(current_state.variables.copy())
            return self.config.relaxation_factor

        # Aitken acceleration formula
        # ω_k = 1 - (x_k - x_{k-1}) / (x_{k+1} - 2*x_k + x_{k-1})

        try:
            x_prev = self._history[-2]  # x_{k-1}
            x_curr = self._history[-1]  # x_k
            x_new = current_state.variables  # x_{k+1}

            # Compute denominators for each variable
            denominators = {}
            for var in x_new.keys():
                if var in x_curr and var in x_prev:
                    denom = x_new[var] - 2*x_curr[var] + x_prev[var]
                    if abs(denom) > 1e-12:
                        denominators[var] = denom

            if denominators:
                # Use average Aitken factor across variables
                aitken_factors = []
                for var, denom in denominators.items():
                    numerator = x_curr[var] - x_prev[var]
                    aitken_factor = 1.0 - numerator / denom
                    # Clamp to reasonable range
                    aitken_factor = max(0.1, min(0.9, aitken_factor))
                    aitken_factors.append(aitken_factor)

                relaxation_factor = np.mean(aitken_factors)
                # Apply damping
                relaxation_factor = (self.config.aitken_damping * self.config.relaxation_factor +
                                   (1 - self.config.aitken_damping) * relaxation_factor)
            else:
                relaxation_factor = self.config.relaxation_factor

            # Update history
            self._history.append(x_new.copy())
            if len(self._history) > 10:
                self._history.pop(0)

            return relaxation_factor

        except (KeyError, ZeroDivisionError, ValueError):
            return self.config.relaxation_factor


class AccelerationController:
    """Controls convergence acceleration methods."""

    def __init__(self, config: AccelerationConfig):
        self.config = config
        self._history = []
        self._residual_history = []

    def accelerate(
        self,
        current_variables: Dict[str, float],
        residuals: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """Apply convergence acceleration to variables."""
        if self.config.method == AccelerationMethod.NONE:
            return current_variables

        elif self.config.method == AccelerationMethod.AITKEN:
            return self._aitken_acceleration(current_variables)

        elif self.config.method == AccelerationMethod.ANDERSON:
            return self._anderson_acceleration(current_variables, residuals)

        elif self.config.method == AccelerationMethod.SIMPLIFIED_NEWTON:
            return self._simplified_newton_acceleration(current_variables, residuals)

        else:
            raise ValueError(f"Unknown acceleration method: {self.config.method}")

    def _aitken_acceleration(self, variables: Dict[str, float]) -> Dict[str, float]:
        """Apply Aitken Δ² acceleration."""
        if len(self._history) < 2:
            self._history.append(variables.copy())
            return variables

        try:
            x_prev2 = self._history[-2]  # x_{k-2}
            x_prev1 = self._history[-1]  # x_{k-1}
            x_curr = variables  # x_k

            accelerated = {}
            for var in variables.keys():
                if var in x_prev1 and var in x_prev2:
                    delta1 = x_prev1[var] - x_prev2[var]
                    delta2 = x_curr[var] - x_prev1[var]

                    if abs(delta2 - delta1) > 1e-12:
                        # Aitken formula: x_acc = x_k - (delta2)² / (delta2 - delta1)
                        accelerated[var] = x_curr[var] - (delta2 * delta2) / (delta2 - delta1)
                    else:
                        accelerated[var] = x_curr[var]
                else:
                    accelerated[var] = x_curr[var]

            self._history.append(variables.copy())
            if len(self._history) > 10:
                self._history.pop(0)

            return accelerated

        except (KeyError, ZeroDivisionError):
            return variables

    def _anderson_acceleration(
        self,
        variables: Dict[str, float],
        residuals: Optional[Dict[str, float]]
    ) -> Dict[str, float]:
        """Apply Anderson acceleration (Anderson mixing)."""
        if residuals is None:
            return variables

        self._history.append(variables.copy())
        self._residual_history.append(residuals.copy())

        if len(self._history) < 2:
            return variables

        # Keep only recent history
        max_depth = min(self.config.anderson_depth, len(self._history) - 1)

        try:
            # Build matrices for Anderson mixing
            var_names = list(variables.keys())
            n_vars = len(var_names)

            # Residual differences matrix
            F = np.zeros((n_vars, max_depth))
            for i in range(max_depth):
                hist_idx = -(i+1)
                for j, var in enumerate(var_names):
                    if var in self._residual_history[hist_idx]:
                        F[j, i] = (self._residual_history[-1][var] -
                                 self._residual_history[hist_idx][var])

            # Solve least squares problem
            if max_depth == 1:
                # Simple case
                alpha = np.array([1.0])
            else:
                try:
                    alpha, _, _, _ = np.linalg.lstsq(F,
                                                   np.array([self._residual_history[-1][var]
                                                           for var in var_names]),
                                                   rcond=None)
                except np.linalg.LinAlgError:
                    return variables

            # Normalize weights
            alpha = np.append(alpha, 1.0 - np.sum(alpha))

            # Compute accelerated solution
            accelerated = {}
            for var in var_names:
                acc_val = 0.0
                for i in range(max_depth + 1):
                    hist_idx = -(i+1)
                    if var in self._history[hist_idx]:
                        acc_val += alpha[i] * self._history[hist_idx][var]

                accelerated[var] = self.config.anderson_beta * acc_val + \
                                 (1 - self.config.anderson_beta) * variables[var]

            # Trim history
            if len(self._history) > self.config.anderson_depth + 5:
                self._history.pop(0)
                self._residual_history.pop(0)

            return accelerated

        except (ValueError, np.linalg.LinAlgError):
            return variables

    def _simplified_newton_acceleration(
        self,
        variables: Dict[str, float],
        residuals: Optional[Dict[str, float]]
    ) -> Dict[str, float]:
        """Apply simplified Newton acceleration with approximate Jacobian."""
        if residuals is None or len(self._history) < 1:
            self._history.append(variables.copy())
            self._residual_history.append(residuals.copy() if residuals else {})
            return variables

        try:
            # Approximate Jacobian using finite differences
            var_names = list(variables.keys())
            n_vars = len(var_names)

            J = np.eye(n_vars)  # Start with identity

            if len(self._history) > 0:
                # Compute approximate Jacobian entries
                prev_vars = self._history[-1]
                prev_residuals = self._residual_history[-1]

                for i, var_i in enumerate(var_names):
                    for j, var_j in enumerate(var_names):
                        dvar = variables[var_j] - prev_vars.get(var_j, 0)
                        dresidual = residuals[var_i] - prev_residuals.get(var_i, 0)

                        if abs(dvar) > 1e-12:
                            J[i, j] = dresidual / dvar

            # Newton step: x_new = x - J^(-1) * F(x)
            residual_vector = np.array([residuals[var] for var in var_names])

            try:
                delta_x = np.linalg.solve(J, residual_vector)
            except np.linalg.LinAlgError:
                # Fallback to simple relaxation if Jacobian is singular
                return variables

            # Apply Newton correction with damping
            accelerated = {}
            for i, var in enumerate(var_names):
                accelerated[var] = variables[var] - 0.1 * delta_x[i]  # 0.1 is damping factor

            self._history.append(variables.copy())
            self._residual_history.append(residuals.copy())

            # Trim history
            if len(self._history) > 5:
                self._history.pop(0)
                self._residual_history.pop(0)

            return accelerated

        except (ValueError, np.linalg.LinAlgError, KeyError):
            return variables


class CouplingIterator:
    """
    Main coupling iteration controller.

    Manages the iterative coupling process between multiple Earth system components
    with convergence checking, relaxation, and acceleration.
    """

    def __init__(
        self,
        convergence_config: ConvergenceConfig,
        relaxation_config: Optional[RelaxationConfig] = None,
        acceleration_config: Optional[AccelerationConfig] = None
    ):
        """
        Initialize coupling iterator.

        Args:
            convergence_config: Configuration for convergence checking
            relaxation_config: Configuration for relaxation methods
            acceleration_config: Configuration for acceleration methods
        """
        self.convergence_config = convergence_config
        self.relaxation_config = relaxation_config or RelaxationConfig()
        self.acceleration_config = acceleration_config or AccelerationConfig()

        self.convergence_checker = MixedConvergenceChecker()
        self.relaxation_controller = RelaxationController(self.relaxation_config)
        self.acceleration_controller = AccelerationController(self.acceleration_config)

        logger.info(f"Initialized CouplingIterator with {convergence_config.method.value} convergence, "
                   f"{relaxation_config.method.value} relaxation, "
                   f"{acceleration_config.method.value} acceleration")

    def iterate_coupling(
        self,
        esm_file: EsmFile,
        initial_variables: Dict[str, float],
        coupling_function: Callable[[Dict[str, float]], Tuple[Dict[str, float], Optional[Dict[str, float]]]],
        **kwargs
    ) -> CouplingResult:
        """
        Perform iterative coupling with convergence control.

        Args:
            esm_file: ESM file defining the coupled system
            initial_variables: Initial values for coupled variables
            coupling_function: Function that performs one coupling step.
                              Should return (updated_variables, residuals)
            **kwargs: Additional arguments for the coupling function

        Returns:
            CouplingResult containing convergence information and iteration history
        """
        import time
        start_time = time.time()

        # Build coupling graph for analysis
        coupling_graph = construct_coupling_graph(esm_file)
        logger.info(f"Constructed coupling graph with {len(coupling_graph.nodes)} nodes "
                   f"and {len(coupling_graph.edges)} edges")

        iteration_history = []
        current_variables = initial_variables.copy()
        previous_state = None

        logger.info(f"Starting coupling iteration with {len(initial_variables)} variables")

        for iteration in range(self.convergence_config.max_iterations):
            logger.debug(f"Coupling iteration {iteration + 1}")

            # Perform coupling step
            try:
                updated_variables, residuals = coupling_function(current_variables, **kwargs)
            except Exception as e:
                logger.error(f"Coupling function failed at iteration {iteration + 1}: {e}")
                return CouplingResult(
                    converged=False,
                    final_state=IterationState(iteration, current_variables),
                    iteration_history=iteration_history,
                    convergence_reason=f"Coupling function error: {e}",
                    total_iterations=iteration + 1,
                    execution_time=time.time() - start_time
                )

            # Apply acceleration
            if self.acceleration_config.method != AccelerationMethod.NONE:
                updated_variables = self.acceleration_controller.accelerate(
                    updated_variables, residuals
                )

            # Compute relaxation factor
            current_state = IterationState(
                iteration=iteration + 1,
                variables=updated_variables,
                residuals=residuals
            )

            relaxation_factor = self.relaxation_controller.compute_relaxation_factor(
                current_state, previous_state, iteration + 1
            )

            # Apply relaxation
            if relaxation_factor < 1.0:
                relaxed_variables = {}
                for var, new_val in updated_variables.items():
                    old_val = current_variables.get(var, 0.0)
                    relaxed_variables[var] = (relaxation_factor * new_val +
                                            (1 - relaxation_factor) * old_val)
                updated_variables = relaxed_variables

            # Update current state with relaxed variables
            current_state.variables = updated_variables
            current_state.relaxation_factor = relaxation_factor

            # Check convergence
            converged, convergence_metrics = self.convergence_checker.check_convergence(
                current_state, previous_state, self.convergence_config
            )
            current_state.convergence_metrics = convergence_metrics

            # Store iteration state
            iteration_history.append(current_state.copy())

            # Log progress
            if convergence_metrics:
                logger.debug(f"Iteration {iteration + 1}: "
                           f"abs_err={convergence_metrics.get('max_absolute_error', 0):.2e}, "
                           f"rel_err={convergence_metrics.get('max_relative_error', 0):.2e}, "
                           f"relax={relaxation_factor:.3f}")

            if converged and iteration + 1 >= self.convergence_config.min_iterations:
                logger.info(f"Coupling converged in {iteration + 1} iterations")
                return CouplingResult(
                    converged=True,
                    final_state=current_state,
                    iteration_history=iteration_history,
                    convergence_reason="Convergence criteria satisfied",
                    total_iterations=iteration + 1,
                    execution_time=time.time() - start_time
                )

            # Update for next iteration
            current_variables = updated_variables
            previous_state = current_state

        # Max iterations reached
        logger.warning(f"Coupling did not converge within {self.convergence_config.max_iterations} iterations")
        return CouplingResult(
            converged=False,
            final_state=iteration_history[-1] if iteration_history else IterationState(0, initial_variables),
            iteration_history=iteration_history,
            convergence_reason="Maximum iterations exceeded",
            total_iterations=self.convergence_config.max_iterations,
            execution_time=time.time() - start_time
        )


# Convenience functions for common use cases

def create_default_coupling_iterator(
    max_iterations: int = 100,
    tolerance: float = 1e-6,
    relaxation_factor: float = 0.5,
    use_acceleration: bool = False
) -> CouplingIterator:
    """
    Create a coupling iterator with sensible defaults.

    Args:
        max_iterations: Maximum number of iterations
        tolerance: Convergence tolerance (absolute and relative)
        relaxation_factor: Fixed relaxation factor
        use_acceleration: Whether to use Aitken acceleration

    Returns:
        Configured CouplingIterator
    """
    convergence_config = ConvergenceConfig(
        method=ConvergenceMethod.MIXED,
        absolute_tolerance=tolerance,
        relative_tolerance=tolerance,
        max_iterations=max_iterations
    )

    relaxation_config = RelaxationConfig(
        method=RelaxationMethod.FIXED,
        relaxation_factor=relaxation_factor
    )

    acceleration_config = AccelerationConfig(
        method=AccelerationMethod.AITKEN if use_acceleration else AccelerationMethod.NONE
    )

    return CouplingIterator(convergence_config, relaxation_config, acceleration_config)


def create_adaptive_coupling_iterator(
    max_iterations: int = 100,
    tolerance: float = 1e-6
) -> CouplingIterator:
    """
    Create a coupling iterator with adaptive relaxation and Anderson acceleration.

    Args:
        max_iterations: Maximum number of iterations
        tolerance: Convergence tolerance

    Returns:
        Configured CouplingIterator with adaptive methods
    """
    convergence_config = ConvergenceConfig(
        method=ConvergenceMethod.MIXED,
        absolute_tolerance=tolerance,
        relative_tolerance=tolerance,
        max_iterations=max_iterations
    )

    relaxation_config = RelaxationConfig(
        method=RelaxationMethod.ADAPTIVE,
        relaxation_factor=0.5
    )

    acceleration_config = AccelerationConfig(
        method=AccelerationMethod.ANDERSON,
        anderson_depth=3
    )

    return CouplingIterator(convergence_config, relaxation_config, acceleration_config)