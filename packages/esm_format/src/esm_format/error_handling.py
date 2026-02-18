"""
Minimal error handling for ESM Format.
This provides only the essential error handling functionality required by validation.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any


class ErrorCode(Enum):
    """Error codes for ESM validation."""
    SCHEMA_VALIDATION_ERROR = "schema_validation_error"
    EQUATION_COUNT_MISMATCH = "equation_count_mismatch"
    UNDEFINED_VARIABLE = "undefined_variable"
    UNDEFINED_SPECIES = "undefined_species"
    UNDEFINED_PARAMETER = "undefined_parameter"
    UNDEFINED_SYSTEM = "undefined_system"
    UNRESOLVED_SCOPED_REF = "unresolved_scoped_ref"
    UNDEFINED_OPERATOR = "undefined_operator"
    INVALID_DISCRETE_PARAM = "invalid_discrete_param"
    NULL_REACTION = "null_reaction"
    MISSING_OBSERVED_EXPR = "missing_observed_expr"
    EVENT_VAR_UNDECLARED = "event_var_undeclared"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    UNIT_MISMATCH = "unit_mismatch"


class Severity(Enum):
    """Error severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ErrorContext:
    """Context information for errors."""
    path: Optional[str] = None
    component: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class FixSuggestion:
    """Suggestion for fixing an error."""
    description: str
    action: Optional[str] = None


@dataclass
class ESMError:
    """ESM validation or processing error."""
    code: ErrorCode
    message: str
    severity: Severity
    context: Optional[ErrorContext] = None
    fix_suggestion: Optional[FixSuggestion] = None


class ErrorCollector:
    """Collects errors and warnings during validation."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def add_error(self, error: ESMError):
        """Add an error to the collection."""
        self.errors.append(error)

    def add_warning(self, warning: ESMError):
        """Add a warning to the collection."""
        self.warnings.append(warning)

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    def get_errors(self) -> list:
        """Get all collected errors."""
        return self.errors.copy()

    def get_warnings(self) -> list:
        """Get all collected warnings."""
        return self.warnings.copy()


class ESMErrorFactory:
    """Factory for creating ESM errors."""

    @staticmethod
    def schema_error(message: str, path: str = None) -> ESMError:
        """Create a schema validation error."""
        return ESMError(
            code=ErrorCode.SCHEMA_VALIDATION_ERROR,
            message=message,
            severity=Severity.ERROR,
            context=ErrorContext(path=path)
        )

    @staticmethod
    def undefined_variable_error(variable: str, component: str) -> ESMError:
        """Create an undefined variable error."""
        return ESMError(
            code=ErrorCode.UNDEFINED_VARIABLE,
            message=f"Variable '{variable}' is not defined",
            severity=Severity.ERROR,
            context=ErrorContext(component=component, details={"variable": variable})
        )

    @staticmethod
    def undefined_operator_error(operator: str, component: str = None) -> ESMError:
        """Create an undefined operator error."""
        return ESMError(
            code=ErrorCode.UNDEFINED_OPERATOR,
            message=f"Operator '{operator}' is not defined",
            severity=Severity.ERROR,
            context=ErrorContext(component=component, details={"operator": operator})
        )

    @staticmethod
    def invalid_discrete_param_error(param: str, component: str = None) -> ESMError:
        """Create an invalid discrete parameter error."""
        return ESMError(
            code=ErrorCode.INVALID_DISCRETE_PARAM,
            message=f"Discrete parameter '{param}' does not match a declared parameter",
            severity=Severity.ERROR,
            context=ErrorContext(component=component, details={"parameter": param})
        )

    @staticmethod
    def null_reaction_error(component: str = None) -> ESMError:
        """Create a null reaction error."""
        return ESMError(
            code=ErrorCode.NULL_REACTION,
            message="Reaction has both substrates: null and products: null",
            severity=Severity.ERROR,
            context=ErrorContext(component=component)
        )

    @staticmethod
    def missing_observed_expr_error(variable: str, component: str = None) -> ESMError:
        """Create a missing observed expression error."""
        return ESMError(
            code=ErrorCode.MISSING_OBSERVED_EXPR,
            message=f"Observed variable '{variable}' is missing its expression field",
            severity=Severity.ERROR,
            context=ErrorContext(component=component, details={"variable": variable})
        )

    @staticmethod
    def event_var_undeclared_error(variable: str, component: str = None) -> ESMError:
        """Create an event variable undeclared error."""
        return ESMError(
            code=ErrorCode.EVENT_VAR_UNDECLARED,
            message=f"Variable '{variable}' in event affects/conditions is not declared",
            severity=Severity.ERROR,
            context=ErrorContext(component=component, details={"variable": variable})
        )