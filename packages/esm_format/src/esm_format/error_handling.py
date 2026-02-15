"""
Comprehensive error handling and diagnostics system for ESM Format.

This module provides:
1. Standardized error codes and messages
2. User-friendly error reporting with fix suggestions
3. Debugging aids for complex coupling issues
4. Performance profiling tools
5. Interactive error exploration helpers
"""

import traceback
import time
import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Union
from enum import Enum
import logging
import sys
from pathlib import Path


class ErrorCode(Enum):
    """Standardized error codes for consistent error handling across all libraries."""

    # Schema and Parsing Errors (1000-1999)
    JSON_PARSE_ERROR = "ESM1001"
    SCHEMA_VALIDATION_ERROR = "ESM1002"
    UNSUPPORTED_VERSION = "ESM1003"
    MISSING_REQUIRED_FIELD = "ESM1004"
    INVALID_FIELD_TYPE = "ESM1005"

    # Structural Validation Errors (2000-2999)
    EQUATION_UNKNOWN_IMBALANCE = "ESM2001"
    UNDEFINED_REFERENCE = "ESM2002"
    INVALID_SCOPE_PATH = "ESM2003"
    CIRCULAR_DEPENDENCY = "ESM2004"
    MISSING_COUPLING_TARGET = "ESM2005"
    INVALID_REACTION_STOICHIOMETRY = "ESM2006"
    UNDECLARED_SPECIES = "ESM2007"
    UNDECLARED_PARAMETER = "ESM2008"
    NULL_NULL_REACTION = "ESM2009"

    # Expression and Mathematical Errors (3000-3999)
    EXPRESSION_PARSE_ERROR = "ESM3001"
    UNDEFINED_VARIABLE = "ESM3002"
    TYPE_MISMATCH = "ESM3003"
    DIVISION_BY_ZERO = "ESM3004"
    MATHEMATICAL_INCONSISTENCY = "ESM3005"
    UNIT_MISMATCH = "ESM3006"
    DIMENSION_ERROR = "ESM3007"

    # Coupling and System Integration Errors (4000-4999)
    COUPLING_RESOLUTION_ERROR = "ESM4001"
    SCOPE_BOUNDARY_VIOLATION = "ESM4002"
    VARIABLE_SHADOWING = "ESM4003"
    DEEP_NESTING_WARNING = "ESM4004"
    UNUSED_VARIABLE = "ESM4005"
    COUPLING_GRAPH_CYCLE = "ESM4006"
    INCOMPATIBLE_DOMAINS = "ESM4007"

    # Simulation and Runtime Errors (5000-5999)
    SIMULATION_CONVERGENCE_ERROR = "ESM5001"
    SOLVER_CONFIGURATION_ERROR = "ESM5002"
    BOUNDARY_CONDITION_ERROR = "ESM5003"
    TIME_SYNCHRONIZATION_ERROR = "ESM5004"
    DATA_LOADER_ERROR = "ESM5005"
    OPERATOR_EXECUTION_ERROR = "ESM5006"

    # Performance and Resource Errors (6000-6999)
    MEMORY_LIMIT_EXCEEDED = "ESM6001"
    COMPUTATION_TIMEOUT = "ESM6002"
    LARGE_SYSTEM_WARNING = "ESM6003"
    INEFFICIENT_COUPLING = "ESM6004"

    # User Interface and Interactive Errors (7000-7999)
    EDITOR_STATE_ERROR = "ESM7001"
    INVALID_USER_INPUT = "ESM7002"
    DISPLAY_RENDERING_ERROR = "ESM7003"


class Severity(Enum):
    """Error severity levels."""
    CRITICAL = "critical"  # System cannot continue
    ERROR = "error"       # Feature won't work but system can continue
    WARNING = "warning"   # Potential issue, but operation can continue
    INFO = "info"         # Informational message
    DEBUG = "debug"       # Debug information


@dataclass
class ErrorContext:
    """Additional context information for errors."""
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    component_name: Optional[str] = None
    operation: Optional[str] = None
    user_input: Optional[Any] = None
    system_state: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class FixSuggestion:
    """Actionable suggestion for fixing an error."""
    description: str
    code_example: Optional[str] = None
    documentation_link: Optional[str] = None
    automated_fix: Optional[Callable[[], None]] = None
    priority: int = 1  # 1 = highest priority


@dataclass
class ESMError:
    """Comprehensive error representation with diagnostics and suggestions."""
    code: ErrorCode
    message: str
    severity: Severity
    path: str = ""
    context: Optional[ErrorContext] = None
    fix_suggestions: List[FixSuggestion] = field(default_factory=list)
    related_errors: List['ESMError'] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    debug_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "code": self.code.value,
            "message": self.message,
            "severity": self.severity.value,
            "path": self.path,
            "timestamp": self.timestamp,
            "context": {
                "file_path": self.context.file_path if self.context else None,
                "line_number": self.context.line_number if self.context else None,
                "column": self.context.column if self.context else None,
                "component_name": self.context.component_name if self.context else None,
                "operation": self.context.operation if self.context else None,
                "performance_metrics": self.context.performance_metrics if self.context else {},
            } if self.context else {},
            "fix_suggestions": [
                {
                    "description": suggestion.description,
                    "code_example": suggestion.code_example,
                    "documentation_link": suggestion.documentation_link,
                    "priority": suggestion.priority
                }
                for suggestion in self.fix_suggestions
            ],
            "debug_info": self.debug_info
        }

    def format_user_friendly(self) -> str:
        """Format error message for end users."""
        lines = []

        # Header with severity and code
        severity_icon = {
            Severity.CRITICAL: "🚫",
            Severity.ERROR: "❌",
            Severity.WARNING: "⚠️",
            Severity.INFO: "ℹ️",
            Severity.DEBUG: "🔍"
        }

        lines.append(f"{severity_icon.get(self.severity, '•')} {self.severity.value.upper()} [{self.code.value}]")
        lines.append(f"   {self.message}")

        if self.path:
            lines.append(f"   Location: {self.path}")

        if self.context and self.context.file_path:
            location_parts = []
            if self.context.file_path:
                location_parts.append(self.context.file_path)
            if self.context.line_number:
                location_parts.append(f"line {self.context.line_number}")
            if self.context.column:
                location_parts.append(f"col {self.context.column}")
            if location_parts:
                lines.append(f"   File: {':'.join(map(str, location_parts))}")

        # Fix suggestions
        if self.fix_suggestions:
            lines.append("")
            lines.append("💡 Suggested fixes:")
            for i, suggestion in enumerate(sorted(self.fix_suggestions, key=lambda s: s.priority), 1):
                lines.append(f"   {i}. {suggestion.description}")
                if suggestion.code_example:
                    lines.append(f"      Example: {suggestion.code_example}")
                if suggestion.documentation_link:
                    lines.append(f"      Docs: {suggestion.documentation_link}")

        return "\n".join(lines)


class ErrorCollector:
    """Collects and manages errors during ESM processing."""

    def __init__(self):
        self.errors: List[ESMError] = []
        self.warnings: List[ESMError] = []
        self.performance_data: Dict[str, float] = {}

    def add_error(self, error: ESMError):
        """Add an error to the collection."""
        if error.severity in [Severity.CRITICAL, Severity.ERROR]:
            self.errors.append(error)
        else:
            self.warnings.append(error)

    def has_errors(self) -> bool:
        """Check if there are any critical errors or errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    def get_summary(self) -> str:
        """Get a summary of all collected errors and warnings."""
        if not self.errors and not self.warnings:
            return "✅ No errors or warnings"

        lines = []
        if self.errors:
            lines.append(f"❌ {len(self.errors)} error(s)")
        if self.warnings:
            lines.append(f"⚠️  {len(self.warnings)} warning(s)")

        return ", ".join(lines)

    def export_report(self, format: str = "json") -> str:
        """Export error report in specified format."""
        all_errors = self.errors + self.warnings

        if format == "json":
            return json.dumps([error.to_dict() for error in all_errors], indent=2)
        elif format == "text":
            return "\n\n".join(error.format_user_friendly() for error in all_errors)
        else:
            raise ValueError(f"Unsupported export format: {format}")


class ESMErrorFactory:
    """Factory for creating standardized ESM errors with helpful suggestions."""

    @staticmethod
    def create_json_parse_error(message: str, file_path: str = "", line_number: int = None) -> ESMError:
        """Create a JSON parse error with fix suggestions."""
        context = ErrorContext(
            file_path=file_path,
            line_number=line_number,
            operation="json_parsing"
        )

        suggestions = [
            FixSuggestion(
                description="Check for missing commas, quotes, or brackets",
                code_example='{"valid": "json", "array": [1, 2, 3]}',
                priority=1
            ),
            FixSuggestion(
                description="Validate JSON syntax using an online JSON validator",
                documentation_link="https://jsonlint.com/",
                priority=2
            )
        ]

        return ESMError(
            code=ErrorCode.JSON_PARSE_ERROR,
            message=f"Failed to parse JSON: {message}",
            severity=Severity.ERROR,
            path=file_path,
            context=context,
            fix_suggestions=suggestions
        )

    @staticmethod
    def create_equation_imbalance_error(model_name: str, num_equations: int, num_unknowns: int,
                                      state_variables: List[str]) -> ESMError:
        """Create equation-unknown imbalance error with detailed suggestions."""
        context = ErrorContext(
            component_name=model_name,
            operation="structural_validation"
        )

        suggestions = []
        if num_equations < num_unknowns:
            diff = num_unknowns - num_equations
            suggestions.append(FixSuggestion(
                description=f"Add {diff} more equation(s) to balance the system",
                code_example=f'"equations": [{{"lhs": "d{state_variables[0]}/dt", "rhs": "expression"}}]',
                priority=1
            ))
        else:
            diff = num_equations - num_unknowns
            suggestions.append(FixSuggestion(
                description=f"Remove {diff} equation(s) or add {diff} more state variable(s)",
                priority=1
            ))

        suggestions.append(FixSuggestion(
            description="Review the mathematical model to ensure proper formulation",
            documentation_link="https://docs.earthsciml.org/esm-format/models/#equation-balance",
            priority=2
        ))

        message = f"Model '{model_name}' has {num_equations} equations but {num_unknowns} unknowns (state variables: {', '.join(state_variables)})"

        return ESMError(
            code=ErrorCode.EQUATION_UNKNOWN_IMBALANCE,
            message=message,
            severity=Severity.ERROR,
            path=f"/models[name='{model_name}']",
            context=context,
            fix_suggestions=suggestions
        )

    @staticmethod
    def create_undefined_reference_error(reference: str, available_variables: List[str] = None,
                                       scope_path: str = "") -> ESMError:
        """Create undefined reference error with smart suggestions."""
        context = ErrorContext(
            operation="reference_resolution"
        )

        suggestions = []

        # Smart suggestions based on available variables
        if available_variables:
            # Find close matches using simple string similarity
            close_matches = []
            ref_lower = reference.lower()
            for var in available_variables:
                if var.lower() in ref_lower or ref_lower in var.lower():
                    close_matches.append(var)

            if close_matches:
                suggestions.append(FixSuggestion(
                    description=f"Did you mean: {', '.join(close_matches[:3])}?",
                    code_example=f'"reference": "{close_matches[0]}"',
                    priority=1
                ))

        suggestions.extend([
            FixSuggestion(
                description="Check variable names and scopes for typos",
                priority=2
            ),
            FixSuggestion(
                description="Ensure the variable is declared in the correct scope",
                documentation_link="https://docs.earthsciml.org/esm-format/scoping/",
                priority=3
            )
        ])

        debug_info = {
            "reference": reference,
            "scope_path": scope_path,
            "available_variables": available_variables or []
        }

        return ESMError(
            code=ErrorCode.UNDEFINED_REFERENCE,
            message=f"Reference '{reference}' is not defined in the current scope",
            severity=Severity.ERROR,
            path=scope_path,
            context=context,
            fix_suggestions=suggestions,
            debug_info=debug_info
        )

    @staticmethod
    def create_performance_warning(operation: str, duration: float, threshold: float = 1.0) -> ESMError:
        """Create performance warning with optimization suggestions."""
        context = ErrorContext(
            operation=operation,
            performance_metrics={"duration_seconds": duration, "threshold_seconds": threshold}
        )

        suggestions = [
            FixSuggestion(
                description="Consider simplifying complex expressions",
                priority=1
            ),
            FixSuggestion(
                description="Check for inefficient coupling patterns",
                documentation_link="https://docs.earthsciml.org/esm-format/performance/",
                priority=2
            ),
            FixSuggestion(
                description="Use performance profiling tools to identify bottlenecks",
                code_example="from esm_format.profiling import profile_operation",
                priority=3
            )
        ]

        return ESMError(
            code=ErrorCode.LARGE_SYSTEM_WARNING,
            message=f"Operation '{operation}' took {duration:.2f}s (threshold: {threshold:.2f}s)",
            severity=Severity.WARNING,
            context=context,
            fix_suggestions=suggestions
        )


class PerformanceProfiler:
    """Performance profiling tool for ESM operations."""

    def __init__(self):
        self.timings: Dict[str, List[float]] = {}
        self.memory_usage: Dict[str, List[float]] = {}
        self.active_timers: Dict[str, float] = {}

    def start_timer(self, operation: str):
        """Start timing an operation."""
        self.active_timers[operation] = time.time()

    def end_timer(self, operation: str) -> float:
        """End timing an operation and return duration."""
        if operation not in self.active_timers:
            return 0.0

        duration = time.time() - self.active_timers[operation]
        del self.active_timers[operation]

        if operation not in self.timings:
            self.timings[operation] = []
        self.timings[operation].append(duration)

        return duration

    def get_report(self) -> Dict[str, Any]:
        """Get performance report."""
        report = {}
        for operation, times in self.timings.items():
            report[operation] = {
                "count": len(times),
                "total_time": sum(times),
                "average_time": sum(times) / len(times) if times else 0,
                "min_time": min(times) if times else 0,
                "max_time": max(times) if times else 0
            }
        return report


class InteractiveErrorExplorer:
    """Interactive tools for exploring and understanding errors."""

    @staticmethod
    def analyze_coupling_issues(esm_file, error_collector: ErrorCollector) -> Dict[str, Any]:
        """Analyze coupling-related issues and provide debugging info."""
        from .coupling_graph import construct_coupling_graph

        analysis = {
            "coupling_graph_valid": True,
            "circular_dependencies": [],
            "orphaned_components": [],
            "complex_coupling_paths": [],
            "suggestions": []
        }

        try:
            graph = construct_coupling_graph(esm_file)

            # Check for circular dependencies
            # This would need actual graph cycle detection
            # For now, just placeholder

            # Check for orphaned components
            all_components = set()
            coupled_components = set()

            for model in esm_file.models:
                all_components.add(model.name)
            for rs in esm_file.reaction_systems:
                all_components.add(rs.name)

            for coupling in esm_file.couplings:
                coupled_components.add(coupling.source_model)
                coupled_components.add(coupling.target_model)

            orphaned = all_components - coupled_components
            if orphaned:
                analysis["orphaned_components"] = list(orphaned)
                analysis["suggestions"].append(
                    "Consider adding coupling entries for isolated components"
                )

        except Exception as e:
            analysis["coupling_graph_valid"] = False
            analysis["error"] = str(e)

        return analysis

    @staticmethod
    def suggest_model_improvements(esm_file, errors: List[ESMError]) -> List[str]:
        """Suggest improvements based on error patterns."""
        suggestions = []

        # Analyze error patterns
        error_codes = [error.code for error in errors]

        if ErrorCode.EQUATION_UNKNOWN_IMBALANCE in error_codes:
            suggestions.append("Review mathematical formulation - ensure ODEs are properly balanced")

        if ErrorCode.UNDEFINED_REFERENCE in error_codes:
            suggestions.append("Check variable scoping and naming conventions")

        if ErrorCode.UNIT_MISMATCH in error_codes:
            suggestions.append("Ensure dimensional consistency across equations")

        # Check for complexity indicators
        total_equations = sum(len(model.equations) for model in esm_file.models)
        total_variables = sum(len(model.variables) for model in esm_file.models)

        if total_equations > 100:
            suggestions.append("Consider modularizing large models into smaller components")

        if len(esm_file.couplings) > 20:
            suggestions.append("Review coupling architecture for potential simplification")

        return suggestions


# Global profiler instance
_global_profiler = PerformanceProfiler()

def get_profiler() -> PerformanceProfiler:
    """Get the global performance profiler instance."""
    return _global_profiler


# Context manager for profiling operations
class profile_operation:
    """Context manager for profiling ESM operations."""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.profiler = get_profiler()

    def __enter__(self):
        self.profiler.start_timer(self.operation_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = self.profiler.end_timer(self.operation_name)

        # Create performance warning if operation is slow
        if duration > 1.0:  # 1 second threshold
            warning = ESMErrorFactory.create_performance_warning(
                self.operation_name, duration, 1.0
            )
            # Could emit warning to global error collector if needed


def setup_error_logging(log_file: Optional[str] = None, level: str = "INFO"):
    """Setup logging for ESM error handling."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Setup handlers
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure root logger for ESM
    logger = logging.getLogger('esm_format')
    logger.setLevel(log_level)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add new handlers
    for handler in handlers:
        logger.addHandler(handler)

    return logger


# Export main classes and functions
__all__ = [
    'ErrorCode', 'Severity', 'ErrorContext', 'FixSuggestion', 'ESMError',
    'ErrorCollector', 'ESMErrorFactory', 'PerformanceProfiler',
    'InteractiveErrorExplorer', 'profile_operation', 'get_profiler',
    'setup_error_logging'
]