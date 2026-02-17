"""
Coupling error handling and recovery for ESM Format.

This module provides comprehensive error handling for coupling failures, including:
1. Error propagation and categorization
2. Recovery strategies and fallback mechanisms
3. Partial execution modes for robustness
4. Detailed diagnostic reporting for debugging
5. Adaptive error tolerance and degradation
"""

import traceback
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Union, Any, Tuple
from enum import Enum
import json
from contextlib import contextmanager

from .error_handling import (
    ErrorCode, Severity, ErrorContext, ESMError, ESMErrorFactory,
    ErrorCollector, FixSuggestion
)
from .coupling_iteration import (
    CouplingIterator, ConvergenceConfig, RelaxationConfig, AccelerationConfig,
    ConvergenceMethod, RelaxationMethod, AccelerationMethod,
    IterationState, CouplingResult
)
from .types import EsmFile


logger = logging.getLogger(__name__)


class CouplingErrorType(Enum):
    """Types of coupling errors that can occur."""
    FUNCTION_FAILURE = "function_failure"           # Coupling function threw exception
    CONVERGENCE_FAILURE = "convergence_failure"     # Failed to converge within limits
    NUMERICAL_INSTABILITY = "numerical_instability" # NaN/Inf values detected
    DOMAIN_ERROR = "domain_error"                   # Variables outside valid ranges
    DEPENDENCY_FAILURE = "dependency_failure"       # Required component unavailable
    TIMEOUT_ERROR = "timeout_error"                 # Operation exceeded time limit
    MEMORY_ERROR = "memory_error"                   # Out of memory during coupling
    COMMUNICATION_ERROR = "communication_error"     # Inter-component communication failed


class RecoveryStrategy(Enum):
    """Strategies for recovering from coupling failures."""
    FAIL_FAST = "fail_fast"                        # Immediately stop on any error
    RETRY_WITH_RELAXATION = "retry_with_relaxation" # Retry with increased relaxation
    PARTIAL_EXECUTION = "partial_execution"         # Continue with available components
    FALLBACK_VALUES = "fallback_values"            # Use fallback/default values
    SIMPLIFIED_MODEL = "simplified_model"           # Switch to simpler coupling
    GRACEFUL_DEGRADATION = "graceful_degradation"   # Gradually reduce functionality


class ExecutionMode(Enum):
    """Modes for handling partial execution."""
    STRICT = "strict"                              # All components must succeed
    BEST_EFFORT = "best_effort"                    # Continue with what works
    ESSENTIAL_ONLY = "essential_only"              # Only critical components required
    DIAGNOSTIC = "diagnostic"                      # Collect maximum diagnostic info


@dataclass
class CouplingErrorContext:
    """Extended context for coupling-specific errors."""
    iteration: int = 0
    component_name: Optional[str] = None
    variable_values: Dict[str, float] = field(default_factory=dict)
    residuals: Optional[Dict[str, float]] = None
    convergence_metrics: Optional[Dict[str, float]] = None
    coupling_graph_state: Optional[Dict[str, Any]] = None
    system_resources: Optional[Dict[str, float]] = None


@dataclass
class CouplingError(ESMError):
    """Specialized error for coupling failures."""
    error_type: CouplingErrorType = CouplingErrorType.FUNCTION_FAILURE
    coupling_context: Optional[CouplingErrorContext] = None
    recovery_attempts: List[Dict[str, Any]] = field(default_factory=list)
    is_recoverable: bool = True

    def add_recovery_attempt(self, strategy: RecoveryStrategy, success: bool, details: str):
        """Record a recovery attempt."""
        self.recovery_attempts.append({
            "strategy": strategy.value,
            "success": success,
            "details": details,
            "timestamp": time.time()
        })


@dataclass
class RecoveryConfig:
    """Configuration for coupling error recovery."""
    max_retry_attempts: int = 3
    retry_delay_seconds: float = 0.1
    timeout_seconds: float = 30.0
    enable_partial_execution: bool = True
    fallback_strategies: List[RecoveryStrategy] = field(default_factory=lambda: [
        RecoveryStrategy.RETRY_WITH_RELAXATION,
        RecoveryStrategy.FALLBACK_VALUES,
        RecoveryStrategy.PARTIAL_EXECUTION
    ])
    essential_components: List[str] = field(default_factory=list)
    variable_bounds: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    default_values: Dict[str, float] = field(default_factory=dict)


@dataclass
class DiagnosticReport:
    """Comprehensive diagnostic report for coupling failures."""
    timestamp: float = field(default_factory=time.time)
    errors: List[CouplingError] = field(default_factory=list)
    warnings: List[CouplingError] = field(default_factory=list)
    system_state: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    recovery_summary: Dict[str, int] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "errors": [error.to_dict() for error in self.errors],
            "warnings": [warning.to_dict() for warning in self.warnings],
            "system_state": self.system_state,
            "performance_metrics": self.performance_metrics,
            "recovery_summary": self.recovery_summary,
            "recommendations": self.recommendations
        }

    def export_json(self) -> str:
        """Export report as formatted JSON."""
        return json.dumps(self.to_dict(), indent=2, default=str)


class CouplingErrorAnalyzer:
    """Analyzes coupling errors to provide insights and recommendations."""

    def __init__(self):
        self.error_patterns: Dict[str, int] = {}
        self.component_reliability: Dict[str, float] = {}

    def analyze_error(self, error: CouplingError, context: CouplingErrorContext) -> List[str]:
        """Analyze an error and provide specific recommendations."""
        recommendations = []

        # Pattern-based analysis
        if error.error_type == CouplingErrorType.CONVERGENCE_FAILURE:
            if context.convergence_metrics:
                abs_error = context.convergence_metrics.get('max_absolute_error', 0)
                rel_error = context.convergence_metrics.get('max_relative_error', 0)

                if abs_error > 1e-3:
                    recommendations.append("Large absolute errors suggest numerical instability - consider smaller time steps")
                elif rel_error > 0.1:
                    recommendations.append("Large relative errors indicate poor initial conditions or model mismatch")
                else:
                    recommendations.append("Increase maximum iterations or relax convergence tolerances")

        elif error.error_type == CouplingErrorType.NUMERICAL_INSTABILITY:
            recommendations.append("Check for division by zero or logarithms of negative numbers")
            recommendations.append("Verify variable bounds and add range checking")
            recommendations.append("Consider using more robust numerical methods")

        elif error.error_type == CouplingErrorType.FUNCTION_FAILURE:
            recommendations.append("Review coupling function implementation for edge cases")
            recommendations.append("Add input validation and error handling within coupling functions")

        # Component-specific analysis
        if context.component_name:
            reliability = self.component_reliability.get(context.component_name, 1.0)
            if reliability < 0.8:
                recommendations.append(f"Component '{context.component_name}' has low reliability ({reliability:.1%}) - consider replacement or improvement")

        return recommendations

    def update_patterns(self, error: CouplingError):
        """Update error pattern tracking."""
        pattern_key = f"{error.error_type.value}_{error.code.value}"
        self.error_patterns[pattern_key] = self.error_patterns.get(pattern_key, 0) + 1

        if error.coupling_context and error.coupling_context.component_name:
            component = error.coupling_context.component_name
            # Simple reliability tracking based on error frequency
            current_reliability = self.component_reliability.get(component, 1.0)
            self.component_reliability[component] = max(0.0, current_reliability - 0.05)


class CouplingRecoveryManager:
    """Manages recovery strategies for coupling failures."""

    def __init__(self, config: RecoveryConfig):
        self.config = config
        self.error_analyzer = CouplingErrorAnalyzer()
        self.active_fallbacks: Dict[str, Any] = {}

    def attempt_recovery(
        self,
        error: CouplingError,
        esm_file: EsmFile,
        current_variables: Dict[str, float],
        coupling_function: Callable,
        **kwargs
    ) -> Tuple[bool, Dict[str, float], Optional[str]]:
        """
        Attempt to recover from a coupling error.

        Returns:
            Tuple of (success, recovered_variables, recovery_method)
        """
        logger.info(f"Attempting recovery from {error.error_type.value} error")

        for strategy in self.config.fallback_strategies:
            try:
                success, variables, details = self._apply_strategy(
                    strategy, error, esm_file, current_variables, coupling_function, **kwargs
                )

                error.add_recovery_attempt(strategy, success, details)

                if success:
                    logger.info(f"Recovery successful using {strategy.value}")
                    return True, variables, strategy.value

            except Exception as recovery_error:
                logger.warning(f"Recovery strategy {strategy.value} failed: {recovery_error}")
                error.add_recovery_attempt(strategy, False, str(recovery_error))

        logger.error("All recovery strategies failed")
        return False, current_variables, None

    def _apply_strategy(
        self,
        strategy: RecoveryStrategy,
        error: CouplingError,
        esm_file: EsmFile,
        variables: Dict[str, float],
        coupling_function: Callable,
        **kwargs
    ) -> Tuple[bool, Dict[str, float], str]:
        """Apply a specific recovery strategy."""

        if strategy == RecoveryStrategy.RETRY_WITH_RELAXATION:
            return self._retry_with_relaxation(error, esm_file, variables, coupling_function, **kwargs)

        elif strategy == RecoveryStrategy.FALLBACK_VALUES:
            return self._apply_fallback_values(variables)

        elif strategy == RecoveryStrategy.PARTIAL_EXECUTION:
            return self._partial_execution(error, variables, coupling_function, **kwargs)

        elif strategy == RecoveryStrategy.SIMPLIFIED_MODEL:
            return self._simplified_model(variables, coupling_function, **kwargs)

        elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            return self._graceful_degradation(error, variables)

        else:
            return False, variables, f"Unknown strategy: {strategy.value}"

    def _retry_with_relaxation(
        self,
        error: CouplingError,
        esm_file: EsmFile,
        variables: Dict[str, float],
        coupling_function: Callable,
        **kwargs
    ) -> Tuple[bool, Dict[str, float], str]:
        """Retry coupling with increased relaxation."""
        try:
            # Create more conservative coupling iterator
            conservative_config = ConvergenceConfig(
                method=ConvergenceMethod.MIXED,
                absolute_tolerance=1e-4,  # Relaxed tolerance
                relative_tolerance=1e-3,
                max_iterations=50,
                min_iterations=1
            )

            relaxation_config = RelaxationConfig(
                method=RelaxationMethod.FIXED,
                relaxation_factor=0.3  # Strong relaxation
            )

            acceleration_config = AccelerationConfig(
                method=AccelerationMethod.NONE  # Disable acceleration for stability
            )

            conservative_iterator = CouplingIterator(
                conservative_config, relaxation_config, acceleration_config
            )

            # Retry with conservative settings
            result = conservative_iterator.iterate_coupling(
                esm_file, variables, coupling_function, **kwargs
            )

            if result.converged:
                return True, result.final_state.variables, f"Converged in {result.total_iterations} iterations with relaxation"
            else:
                return False, variables, f"Still did not converge with relaxation after {result.total_iterations} iterations"

        except Exception as e:
            return False, variables, f"Relaxation retry failed: {e}"

    def _apply_fallback_values(self, variables: Dict[str, float]) -> Tuple[bool, Dict[str, float], str]:
        """Apply fallback values for failed variables."""
        recovered_variables = variables.copy()
        fallback_count = 0

        for var_name, default_value in self.config.default_values.items():
            if var_name in variables:
                # Check if variable is problematic (NaN, Inf, out of bounds)
                current_value = variables[var_name]
                is_problematic = (
                    not isinstance(current_value, (int, float)) or
                    current_value != current_value or  # NaN check
                    abs(current_value) == float('inf')
                )

                # Check bounds if specified
                if var_name in self.config.variable_bounds:
                    min_val, max_val = self.config.variable_bounds[var_name]
                    is_problematic = is_problematic or not (min_val <= current_value <= max_val)

                if is_problematic:
                    recovered_variables[var_name] = default_value
                    fallback_count += 1

        success = fallback_count > 0
        details = f"Applied fallback values to {fallback_count} variables" if success else "No fallback values needed"

        return success, recovered_variables, details

    def _partial_execution(
        self,
        error: CouplingError,
        variables: Dict[str, float],
        coupling_function: Callable,
        **kwargs
    ) -> Tuple[bool, Dict[str, float], str]:
        """Continue execution with subset of components."""
        if not self.config.enable_partial_execution:
            return False, variables, "Partial execution disabled"

        try:
            # Create a safe wrapper that handles component failures
            def safe_coupling_function(vars_dict: Dict[str, float], **func_kwargs):
                try:
                    return coupling_function(vars_dict, **func_kwargs)
                except Exception as e:
                    logger.warning(f"Component failed in partial execution: {e}")
                    # Return unchanged variables with zero residuals
                    return vars_dict, {k: 0.0 for k in vars_dict.keys()}

            # Try with the safe wrapper
            updated_vars, residuals = safe_coupling_function(variables, **kwargs)

            return True, updated_vars, "Continued with partial execution (some components may have failed)"

        except Exception as e:
            return False, variables, f"Partial execution failed: {e}"

    def _simplified_model(
        self,
        variables: Dict[str, float],
        coupling_function: Callable,
        **kwargs
    ) -> Tuple[bool, Dict[str, float], str]:
        """Switch to a simplified coupling model."""
        try:
            # Create simplified linear coupling
            def simplified_coupling(vars_dict: Dict[str, float], **func_kwargs):
                # Simple linear relaxation towards equilibrium
                equilibrium = sum(vars_dict.values()) / len(vars_dict) if vars_dict else 0.0

                updated = {}
                residuals = {}
                for var, value in vars_dict.items():
                    # Simple relaxation towards mean
                    new_value = 0.9 * value + 0.1 * equilibrium
                    updated[var] = new_value
                    residuals[var] = new_value - value

                return updated, residuals

            updated_vars, residuals = simplified_coupling(variables, **kwargs)
            return True, updated_vars, "Switched to simplified linear coupling model"

        except Exception as e:
            return False, variables, f"Simplified model failed: {e}"

    def _graceful_degradation(
        self,
        error: CouplingError,
        variables: Dict[str, float]
    ) -> Tuple[bool, Dict[str, float], str]:
        """Gradually reduce system functionality."""
        try:
            degraded_variables = {}

            # Keep only essential variables
            essential_vars = set(self.config.essential_components)
            if essential_vars:
                for var_name, value in variables.items():
                    if var_name in essential_vars or not essential_vars:
                        # Apply conservative bounds
                        if var_name in self.config.variable_bounds:
                            min_val, max_val = self.config.variable_bounds[var_name]
                            value = max(min_val, min(max_val, value))
                        degraded_variables[var_name] = value
            else:
                degraded_variables = variables.copy()

            return True, degraded_variables, f"Degraded to {len(degraded_variables)} essential variables"

        except Exception as e:
            return False, variables, f"Graceful degradation failed: {e}"


class RobustCouplingIterator:
    """
    Coupling iterator with comprehensive error handling and recovery.

    This class wraps the standard CouplingIterator with robust error handling,
    recovery strategies, and diagnostic capabilities.
    """

    def __init__(
        self,
        base_iterator: CouplingIterator,
        recovery_config: Optional[RecoveryConfig] = None,
        execution_mode: ExecutionMode = ExecutionMode.BEST_EFFORT
    ):
        self.base_iterator = base_iterator
        self.recovery_config = recovery_config or RecoveryConfig()
        self.execution_mode = execution_mode
        self.recovery_manager = CouplingRecoveryManager(self.recovery_config)
        self.error_collector = ErrorCollector()
        self.diagnostic_report = DiagnosticReport()

    def iterate_coupling_robust(
        self,
        esm_file: EsmFile,
        initial_variables: Dict[str, float],
        coupling_function: Callable,
        **kwargs
    ) -> Tuple[CouplingResult, DiagnosticReport]:
        """
        Perform robust coupling iteration with error handling.

        Returns:
            Tuple of (CouplingResult, DiagnosticReport)
        """
        start_time = time.time()

        try:
            # Validate inputs
            self._validate_inputs(esm_file, initial_variables)

            # Wrap coupling function with error handling
            safe_coupling_function = self._create_safe_coupling_function(coupling_function)

            # Attempt coupling with error handling
            with self._timeout_context(self.recovery_config.timeout_seconds):
                result = self._attempt_coupling_with_recovery(
                    esm_file, initial_variables, safe_coupling_function, **kwargs
                )

            # Generate diagnostic report
            self._finalize_diagnostic_report(result, time.time() - start_time)

            return result, self.diagnostic_report

        except Exception as e:
            logger.error(f"Critical error in robust coupling iteration: {e}")

            # Create error result
            error_result = CouplingResult(
                converged=False,
                final_state=IterationState(0, initial_variables),
                iteration_history=[],
                convergence_reason=f"Critical error: {e}",
                total_iterations=0,
                execution_time=time.time() - start_time
            )

            # Add critical error to report
            critical_error = CouplingError(
                code=ErrorCode.SIMULATION_CONVERGENCE_ERROR,
                message=f"Critical coupling failure: {e}",
                severity=Severity.CRITICAL,
                error_type=CouplingErrorType.FUNCTION_FAILURE,
                coupling_context=CouplingErrorContext()
            )
            self.error_collector.add_error(critical_error)
            self._finalize_diagnostic_report(error_result, time.time() - start_time)

            return error_result, self.diagnostic_report

    def _validate_inputs(self, esm_file: EsmFile, variables: Dict[str, float]):
        """Validate inputs before coupling."""
        if not variables:
            raise ValueError("Initial variables cannot be empty")

        # Check for invalid values
        for var_name, value in variables.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Variable '{var_name}' must be numeric, got {type(value)}")
            if value != value:  # NaN check
                raise ValueError(f"Variable '{var_name}' is NaN")
            if abs(value) == float('inf'):
                raise ValueError(f"Variable '{var_name}' is infinite")

            # Check bounds if specified
            if var_name in self.recovery_config.variable_bounds:
                min_val, max_val = self.recovery_config.variable_bounds[var_name]
                if not (min_val <= value <= max_val):
                    warning = CouplingError(
                        code=ErrorCode.COUPLING_RESOLUTION_ERROR,
                        message=f"Variable '{var_name}' value {value} outside bounds [{min_val}, {max_val}]",
                        severity=Severity.WARNING,
                        error_type=CouplingErrorType.DOMAIN_ERROR
                    )
                    self.error_collector.add_error(warning)

    def _create_safe_coupling_function(self, original_function: Callable) -> Callable:
        """Create a wrapper that handles coupling function errors."""
        def safe_function(variables: Dict[str, float], **kwargs):
            try:
                return original_function(variables, **kwargs)
            except Exception as e:
                logger.warning(f"Coupling function error: {e}")

                # Create error context
                context = CouplingErrorContext(
                    variable_values=variables.copy(),
                    component_name=kwargs.get('component_name', 'unknown')
                )

                # Determine error type
                error_type = CouplingErrorType.FUNCTION_FAILURE
                if "timeout" in str(e).lower():
                    error_type = CouplingErrorType.TIMEOUT_ERROR
                elif "memory" in str(e).lower():
                    error_type = CouplingErrorType.MEMORY_ERROR
                elif any(keyword in str(e).lower() for keyword in ["nan", "inf", "overflow"]):
                    error_type = CouplingErrorType.NUMERICAL_INSTABILITY

                # Create coupling error
                coupling_error = CouplingError(
                    code=ErrorCode.OPERATOR_EXECUTION_ERROR,
                    message=f"Coupling function failed: {e}",
                    severity=Severity.ERROR,
                    error_type=error_type,
                    coupling_context=context
                )

                # Attempt recovery
                if self.execution_mode != ExecutionMode.STRICT:
                    recovered, new_variables, recovery_method = self.recovery_manager.attempt_recovery(
                        coupling_error, None, variables, original_function, **kwargs
                    )

                    if recovered:
                        logger.info(f"Recovered from coupling error using {recovery_method}")
                        self.error_collector.add_error(coupling_error)
                        return new_variables, {k: 0.0 for k in new_variables.keys()}

                # If recovery failed or strict mode, re-raise
                self.error_collector.add_error(coupling_error)
                raise e

        return safe_function

    def _attempt_coupling_with_recovery(
        self,
        esm_file: EsmFile,
        initial_variables: Dict[str, float],
        coupling_function: Callable,
        **kwargs
    ) -> CouplingResult:
        """Attempt coupling iteration with multiple recovery attempts."""

        for attempt in range(self.recovery_config.max_retry_attempts):
            try:
                logger.info(f"Coupling attempt {attempt + 1}/{self.recovery_config.max_retry_attempts}")

                result = self.base_iterator.iterate_coupling(
                    esm_file, initial_variables, coupling_function, **kwargs
                )

                # Check for convergence failure
                if not result.converged:
                    context = CouplingErrorContext(
                        iteration=result.total_iterations,
                        variable_values=result.final_state.variables
                    )

                    if result.final_state.convergence_metrics:
                        context.convergence_metrics = result.final_state.convergence_metrics

                    convergence_error = CouplingError(
                        code=ErrorCode.SIMULATION_CONVERGENCE_ERROR,
                        message=f"Coupling failed to converge: {result.convergence_reason}",
                        severity=Severity.ERROR,
                        error_type=CouplingErrorType.CONVERGENCE_FAILURE,
                        coupling_context=context
                    )

                    # Attempt recovery for convergence failure
                    if attempt < self.recovery_config.max_retry_attempts - 1:
                        recovered, new_variables, recovery_method = self.recovery_manager.attempt_recovery(
                            convergence_error, esm_file, initial_variables, coupling_function, **kwargs
                        )

                        if recovered:
                            logger.info(f"Recovered from convergence failure using {recovery_method}")
                            initial_variables = new_variables  # Use recovered values for next attempt
                            self.error_collector.add_error(convergence_error)
                            continue

                    self.error_collector.add_error(convergence_error)

                return result

            except Exception as e:
                logger.error(f"Coupling attempt {attempt + 1} failed: {e}")

                if attempt < self.recovery_config.max_retry_attempts - 1:
                    # Wait before retry
                    if self.recovery_config.retry_delay_seconds > 0:
                        time.sleep(self.recovery_config.retry_delay_seconds)
                else:
                    # Final attempt failed, re-raise
                    raise e

        # Should not reach here, but fallback
        return CouplingResult(
            converged=False,
            final_state=IterationState(0, initial_variables),
            iteration_history=[],
            convergence_reason="All recovery attempts exhausted",
            total_iterations=0
        )

    @contextmanager
    def _timeout_context(self, timeout_seconds: float):
        """Context manager for timeout handling."""
        # Simple timeout implementation - in practice you might use signal or threading
        start_time = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                logger.warning(f"Operation took {elapsed:.2f}s (timeout: {timeout_seconds:.2f}s)")

    def _finalize_diagnostic_report(self, result: CouplingResult, execution_time: float):
        """Finalize the diagnostic report."""
        self.diagnostic_report.errors = self.error_collector.errors
        self.diagnostic_report.warnings = self.error_collector.warnings

        # Add performance metrics
        self.diagnostic_report.performance_metrics = {
            "total_execution_time": execution_time,
            "coupling_iterations": result.total_iterations,
            "convergence_achieved": result.converged,
            "average_time_per_iteration": execution_time / max(1, result.total_iterations)
        }

        # Add system state
        self.diagnostic_report.system_state = {
            "final_variables": result.final_state.variables,
            "convergence_reason": result.convergence_reason,
            "error_count": len(self.error_collector.errors),
            "warning_count": len(self.error_collector.warnings)
        }

        # Generate recovery summary
        recovery_summary = {}
        for error in self.error_collector.errors:
            if isinstance(error, CouplingError):
                for attempt in error.recovery_attempts:
                    strategy = attempt["strategy"]
                    recovery_summary[strategy] = recovery_summary.get(strategy, 0) + 1
        self.diagnostic_report.recovery_summary = recovery_summary

        # Generate recommendations
        recommendations = []
        if not result.converged:
            recommendations.append("Consider increasing maximum iterations or relaxing convergence tolerances")
        if len(self.error_collector.errors) > 0:
            recommendations.append("Review error details for specific improvement suggestions")
        if execution_time > 10.0:
            recommendations.append("Performance is slow - consider optimizing coupling functions or reducing system complexity")

        # Add analyzer recommendations
        for error in self.error_collector.errors:
            if isinstance(error, CouplingError) and error.coupling_context:
                error_recommendations = self.recovery_manager.error_analyzer.analyze_error(error, error.coupling_context)
                recommendations.extend(error_recommendations)

        self.diagnostic_report.recommendations = list(set(recommendations))  # Remove duplicates


# Convenience functions for creating robust iterators

def create_robust_coupling_iterator(
    convergence_config: Optional[ConvergenceConfig] = None,
    recovery_config: Optional[RecoveryConfig] = None,
    execution_mode: ExecutionMode = ExecutionMode.BEST_EFFORT,
    use_acceleration: bool = False
) -> RobustCouplingIterator:
    """
    Create a robust coupling iterator with sensible defaults.

    Args:
        convergence_config: Configuration for convergence checking
        recovery_config: Configuration for error recovery
        execution_mode: How to handle partial failures
        use_acceleration: Whether to use convergence acceleration

    Returns:
        Configured RobustCouplingIterator
    """
    if convergence_config is None:
        convergence_config = ConvergenceConfig(
            method=ConvergenceMethod.MIXED,
            absolute_tolerance=1e-6,
            relative_tolerance=1e-4,
            max_iterations=100
        )

    relaxation_config = RelaxationConfig(
        method=RelaxationMethod.ADAPTIVE,
        relaxation_factor=0.5
    )

    acceleration_config = AccelerationConfig(
        method=AccelerationMethod.AITKEN if use_acceleration else AccelerationMethod.NONE
    )

    base_iterator = CouplingIterator(convergence_config, relaxation_config, acceleration_config)

    if recovery_config is None:
        recovery_config = RecoveryConfig()

    return RobustCouplingIterator(base_iterator, recovery_config, execution_mode)


def create_fault_tolerant_iterator(
    max_iterations: int = 200,
    tolerance: float = 1e-4,
    timeout_seconds: float = 60.0
) -> RobustCouplingIterator:
    """
    Create a fault-tolerant iterator optimized for robustness over performance.

    Args:
        max_iterations: Maximum coupling iterations
        tolerance: Convergence tolerance
        timeout_seconds: Maximum execution time

    Returns:
        Fault-tolerant RobustCouplingIterator
    """
    convergence_config = ConvergenceConfig(
        method=ConvergenceMethod.MIXED,
        absolute_tolerance=tolerance,
        relative_tolerance=tolerance * 10,
        max_iterations=max_iterations
    )

    recovery_config = RecoveryConfig(
        max_retry_attempts=5,
        timeout_seconds=timeout_seconds,
        enable_partial_execution=True,
        fallback_strategies=[
            RecoveryStrategy.RETRY_WITH_RELAXATION,
            RecoveryStrategy.FALLBACK_VALUES,
            RecoveryStrategy.SIMPLIFIED_MODEL,
            RecoveryStrategy.PARTIAL_EXECUTION,
            RecoveryStrategy.GRACEFUL_DEGRADATION
        ]
    )

    return create_robust_coupling_iterator(
        convergence_config=convergence_config,
        recovery_config=recovery_config,
        execution_mode=ExecutionMode.BEST_EFFORT,
        use_acceleration=False  # Disable for maximum stability
    )


# Export main classes and functions
__all__ = [
    'CouplingErrorType', 'RecoveryStrategy', 'ExecutionMode',
    'CouplingErrorContext', 'CouplingError', 'RecoveryConfig',
    'DiagnosticReport', 'CouplingErrorAnalyzer', 'CouplingRecoveryManager',
    'RobustCouplingIterator', 'create_robust_coupling_iterator',
    'create_fault_tolerant_iterator'
]