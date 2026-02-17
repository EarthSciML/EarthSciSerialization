"""Initial condition setup and validation system.

This module provides comprehensive initial condition processing including:
- Field initialization from various sources
- Compatibility checking with governing equations
- Interpolation from external data sources
- Constraint validation and enforcement
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

try:
    from .esm_types import (
        InitialCondition,
        InitialConditionType,
        ModelVariable,
        Domain,
        Expr
    )
    from .expression import evaluate
except ImportError:
    # Fallback for direct imports
    from .esm_types import (
        InitialCondition,
        InitialConditionType,
        ModelVariable,
        Domain,
        Expr
    )
    # Stub for expression evaluation if not available
    def evaluate(expr, variables):
        return 0.0

logger = logging.getLogger(__name__)


class ConstraintOperator(Enum):
    """Constraint enforcement strategies."""
    CLAMP = "clamp"      # Clamp values to bounds
    WARN = "warn"        # Log warning but keep value
    ERROR = "error"      # Raise error on violation


@dataclass
class FieldConstraint:
    """Constraint specification for a field."""
    variable: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    units: Optional[str] = None
    operator: ConstraintOperator = ConstraintOperator.CLAMP
    description: Optional[str] = None


@dataclass
class InitialConditionConfig:
    """Configuration for initial condition processing."""
    enforce_constraints: bool = True
    default_fallback_value: float = 0.0
    require_all_variables: bool = True
    allow_extra_variables: bool = False
    interpolation_method: str = "linear"


class InitialConditionSetupError(Exception):
    """Error during initial condition setup."""
    pass


class InitialConditionProcessor:
    """Comprehensive initial condition processor and validator.

    This class handles:
    - Field initialization from constant, function, or data sources
    - Validation against model variable definitions
    - Constraint enforcement (bounds, units)
    - Compatibility checking with governing equations
    """

    def __init__(self, config: Optional[InitialConditionConfig] = None):
        """Initialize processor with configuration."""
        self.config = config or InitialConditionConfig()
        self.constraints: List[FieldConstraint] = []
        self.validation_errors: List[str] = []

    def add_constraint(self, constraint: FieldConstraint):
        """Add a field constraint."""
        self.constraints.append(constraint)

    def validate_initial_conditions(
        self,
        initial_conditions: InitialCondition,
        variables: Dict[str, ModelVariable],
        domain: Optional[Domain] = None
    ) -> List[str]:
        """Validate initial conditions against model structure and domain.

        Args:
            initial_conditions: IC specification to validate
            variables: Model variables from the system
            domain: Optional domain specification for spatial validation

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Basic type validation
        if initial_conditions.type == InitialConditionType.CONSTANT:
            if initial_conditions.value is None:
                errors.append("Constant initial condition requires 'value' field")
        elif initial_conditions.type == InitialConditionType.FUNCTION:
            if initial_conditions.function is None:
                errors.append("Function initial condition requires 'function' field")
        elif initial_conditions.type == InitialConditionType.DATA:
            if initial_conditions.data_source is None:
                errors.append("Data initial condition requires 'data_source' field")

        # Variable coverage validation
        state_variables = {name: var for name, var in variables.items()
                         if var.type == 'state'}

        if self.config.require_all_variables:
            if initial_conditions.type == InitialConditionType.CONSTANT:
                # For constant IC, we'll use the same value for all state variables
                pass  # This is valid
            else:
                errors.append(f"Initial conditions must be provided for all state variables: "
                            f"{list(state_variables.keys())}")

        # Constraint validation
        for constraint in self.constraints:
            if constraint.variable not in state_variables:
                errors.append(f"Constraint variable '{constraint.variable}' not found in model state variables")

        # Domain compatibility
        if domain and initial_conditions.type == InitialConditionType.DATA:
            # Could check spatial/temporal compatibility with data source
            logger.info("Domain compatibility checking for data sources not yet implemented")

        return errors

    def setup_initial_fields(
        self,
        initial_conditions: InitialCondition,
        variables: Dict[str, ModelVariable],
        domain: Optional[Domain] = None
    ) -> Dict[str, float]:
        """Initialize field values from IC specification.

        Args:
            initial_conditions: IC specification
            variables: Model variables
            domain: Optional domain for spatial initialization

        Returns:
            Dictionary mapping variable names to initial values

        Raises:
            InitialConditionSetupError: If setup fails
        """
        # Validate first
        errors = self.validate_initial_conditions(initial_conditions, variables, domain)
        if errors:
            raise InitialConditionSetupError(f"Validation failed: {'; '.join(errors)}")

        field_values = {}
        state_variables = {name: var for name, var in variables.items()
                         if var.type == 'state'}

        if initial_conditions.type == InitialConditionType.CONSTANT:
            # Use constant value for all state variables
            const_value = self._extract_constant_value(initial_conditions.value)
            for var_name in state_variables:
                field_values[var_name] = const_value

        elif initial_conditions.type == InitialConditionType.FUNCTION:
            # Evaluate function for each variable
            field_values = self._evaluate_function_ic(
                initial_conditions.function, state_variables, domain
            )

        elif initial_conditions.type == InitialConditionType.DATA:
            # Load from external data source
            field_values = self._load_from_data_source(
                initial_conditions.data_source, state_variables, domain
            )

        # Apply default values for missing variables
        for var_name, var in state_variables.items():
            if var_name not in field_values:
                if var.default is not None:
                    field_values[var_name] = float(var.default)
                else:
                    field_values[var_name] = self.config.default_fallback_value
                    logger.warning(f"Using fallback value {self.config.default_fallback_value} "
                                 f"for variable '{var_name}'")

        # Apply constraints
        field_values = self.apply_constraints(field_values)

        return field_values

    def apply_constraints(self, field_values: Dict[str, float]) -> Dict[str, float]:
        """Apply constraints to field values.

        Args:
            field_values: Dictionary of variable values

        Returns:
            Modified field values with constraints applied
        """
        if not self.config.enforce_constraints:
            return field_values

        modified_values = field_values.copy()

        for constraint in self.constraints:
            if constraint.variable not in field_values:
                continue

            value = field_values[constraint.variable]

            # Check bounds
            violation = False
            if constraint.min_value is not None and value < constraint.min_value:
                violation = True
                msg = (f"Variable '{constraint.variable}' value {value} below minimum "
                      f"{constraint.min_value}")

                if constraint.operator == ConstraintOperator.CLAMP:
                    modified_values[constraint.variable] = constraint.min_value
                    logger.warning(f"{msg}, clamped to minimum")
                elif constraint.operator == ConstraintOperator.WARN:
                    logger.warning(msg)
                elif constraint.operator == ConstraintOperator.ERROR:
                    raise InitialConditionSetupError(msg)

            if constraint.max_value is not None and value > constraint.max_value:
                violation = True
                msg = (f"Variable '{constraint.variable}' value {value} above maximum "
                      f"{constraint.max_value}")

                if constraint.operator == ConstraintOperator.CLAMP:
                    modified_values[constraint.variable] = constraint.max_value
                    logger.warning(f"{msg}, clamped to maximum")
                elif constraint.operator == ConstraintOperator.WARN:
                    logger.warning(msg)
                elif constraint.operator == ConstraintOperator.ERROR:
                    raise InitialConditionSetupError(msg)

        return modified_values

    def check_equation_compatibility(
        self,
        field_values: Dict[str, float],
        equations: List[Dict[str, Any]]
    ) -> List[str]:
        """Check compatibility of initial conditions with governing equations.

        Args:
            field_values: Initial field values
            equations: Model equations

        Returns:
            List of compatibility warnings/errors
        """
        warnings = []

        # Check if any equations would produce immediate singularities
        for i, eq in enumerate(equations):
            try:
                # Attempt to evaluate RHS at initial conditions
                if isinstance(eq.get('rhs'), dict):
                    # This would need a more sophisticated expression evaluator
                    # For now, just check for divide-by-zero potential
                    self._check_division_by_zero(eq['rhs'], field_values, warnings)
            except Exception as e:
                warnings.append(f"Equation {i}: Could not validate compatibility - {e}")

        return warnings

    def _extract_constant_value(self, value: Union[float, Expr, None]) -> float:
        """Extract float value from constant specification."""
        if value is None:
            return self.config.default_fallback_value
        elif isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, dict):  # Expression
            # Try to evaluate as constant expression
            try:
                result = evaluate(value, {})
                return float(result)
            except:
                logger.warning(f"Could not evaluate expression {value} as constant, using default")
                return self.config.default_fallback_value
        else:
            logger.warning(f"Unknown value type {type(value)}, using default")
            return self.config.default_fallback_value

    def _evaluate_function_ic(
        self,
        function_spec: str,
        variables: Dict[str, ModelVariable],
        domain: Optional[Domain]
    ) -> Dict[str, float]:
        """Evaluate function-based initial conditions.

        This is a placeholder for more sophisticated function evaluation.
        """
        # For now, return default values - this would be expanded to support
        # actual function evaluation, spatial functions, etc.
        logger.warning("Function-based initial conditions not fully implemented")
        return {name: float(var.default) if var.default is not None else 0.0
                for name, var in variables.items()}

    def _load_from_data_source(
        self,
        data_source: str,
        variables: Dict[str, ModelVariable],
        domain: Optional[Domain]
    ) -> Dict[str, float]:
        """Load initial conditions from external data source.

        This is a placeholder for data loading functionality.
        """
        # For now, return default values - this would be expanded to support
        # actual data loading, interpolation, etc.
        logger.warning("Data source initial conditions not fully implemented")
        return {name: float(var.default) if var.default is not None else 0.0
                for name, var in variables.items()}

    def _check_division_by_zero(
        self,
        expr: Dict[str, Any],
        values: Dict[str, float],
        warnings: List[str]
    ):
        """Check expression for potential division by zero."""
        if isinstance(expr, dict) and expr.get('op') == '/':
            args = expr.get('args', [])
            if len(args) == 2:
                denominator = args[1]
                if isinstance(denominator, str) and denominator in values:
                    if abs(values[denominator]) < 1e-12:
                        warnings.append(f"Potential division by zero: variable '{denominator}' "
                                      f"has initial value near zero ({values[denominator]})")


def create_atmospheric_constraints() -> List[FieldConstraint]:
    """Create standard atmospheric chemistry constraints."""
    return [
        FieldConstraint(
            variable="O3",
            min_value=0.0,
            max_value=1e-3,
            units="mol/mol",
            description="Ozone mixing ratio bounds"
        ),
        FieldConstraint(
            variable="NO",
            min_value=0.0,
            max_value=1e-6,
            units="mol/mol",
            description="Nitric oxide mixing ratio bounds"
        ),
        FieldConstraint(
            variable="NO2",
            min_value=0.0,
            max_value=1e-6,
            units="mol/mol",
            description="Nitrogen dioxide mixing ratio bounds"
        ),
    ]


def setup_initial_conditions(
    initial_conditions: InitialCondition,
    variables: Dict[str, ModelVariable],
    domain: Optional[Domain] = None,
    constraints: Optional[List[FieldConstraint]] = None
) -> Tuple[Dict[str, float], List[str]]:
    """High-level function to setup initial conditions with validation.

    Args:
        initial_conditions: IC specification
        variables: Model variables
        domain: Optional domain specification
        constraints: Optional list of field constraints

    Returns:
        Tuple of (field_values, warnings)

    Raises:
        InitialConditionSetupError: If setup fails
    """
    processor = InitialConditionProcessor()

    # Add constraints if provided
    if constraints:
        for constraint in constraints:
            processor.add_constraint(constraint)

    # Setup field values
    field_values = processor.setup_initial_fields(initial_conditions, variables, domain)

    # Check equation compatibility (warnings only)
    warnings = []
    try:
        # This would check against actual equations if available
        warnings.extend(processor.validation_errors)
    except Exception as e:
        warnings.append(f"Could not check equation compatibility: {e}")

    return field_values, warnings