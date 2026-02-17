"""Tests for initial condition setup and validation system."""

import pytest
from typing import Dict

from esm_format.types import (
    InitialCondition,
    InitialConditionType,
    ModelVariable
)
from esm_format.initial_conditions_setup import (
    InitialConditionProcessor,
    InitialConditionConfig,
    FieldConstraint,
    ConstraintOperator,
    InitialConditionSetupError,
    setup_initial_conditions,
    create_atmospheric_constraints
)


def create_test_variables() -> Dict[str, ModelVariable]:
    """Create test model variables."""
    return {
        "O3": ModelVariable(
            type="state",
            units="mol/mol",
            default=1e-8,
            description="Ozone mixing ratio"
        ),
        "NO": ModelVariable(
            type="state",
            units="mol/mol",
            default=1e-10,
            description="Nitric oxide mixing ratio"
        ),
        "NO2": ModelVariable(
            type="state",
            units="mol/mol",
            default=1e-10,
            description="Nitrogen dioxide mixing ratio"
        ),
        "T": ModelVariable(
            type="parameter",
            units="K",
            default=298.15,
            description="Temperature"
        )
    }


class TestInitialConditionProcessor:
    """Test the InitialConditionProcessor class."""

    def test_processor_creation(self):
        """Test processor creation with default config."""
        processor = InitialConditionProcessor()
        assert processor.config.enforce_constraints is True
        assert processor.config.default_fallback_value == 0.0
        assert len(processor.constraints) == 0

    def test_processor_with_custom_config(self):
        """Test processor with custom configuration."""
        config = InitialConditionConfig(
            enforce_constraints=False,
            default_fallback_value=1e-12,
            require_all_variables=False
        )
        processor = InitialConditionProcessor(config)
        assert processor.config.enforce_constraints is False
        assert processor.config.default_fallback_value == 1e-12
        assert processor.config.require_all_variables is False

    def test_add_constraint(self):
        """Test adding constraints to processor."""
        processor = InitialConditionProcessor()
        constraint = FieldConstraint(
            variable="O3",
            min_value=0.0,
            max_value=1e-3
        )
        processor.add_constraint(constraint)
        assert len(processor.constraints) == 1
        assert processor.constraints[0].variable == "O3"

    def test_validate_constant_ic_valid(self):
        """Test validation of valid constant initial conditions."""
        processor = InitialConditionProcessor()
        variables = create_test_variables()

        ic = InitialCondition(
            type=InitialConditionType.CONSTANT,
            value=1e-9
        )

        errors = processor.validate_initial_conditions(ic, variables)
        assert len(errors) == 0

    def test_validate_constant_ic_missing_value(self):
        """Test validation fails for constant IC without value."""
        processor = InitialConditionProcessor()
        variables = create_test_variables()

        ic = InitialCondition(
            type=InitialConditionType.CONSTANT,
            value=None
        )

        errors = processor.validate_initial_conditions(ic, variables)
        assert len(errors) == 1
        assert "requires 'value' field" in errors[0]

    def test_validate_function_ic_missing_function(self):
        """Test validation fails for function IC without function."""
        processor = InitialConditionProcessor()
        variables = create_test_variables()

        ic = InitialCondition(
            type=InitialConditionType.FUNCTION,
            function=None
        )

        errors = processor.validate_initial_conditions(ic, variables)
        assert len(errors) == 1
        assert "requires 'function' field" in errors[0]

    def test_validate_data_ic_missing_source(self):
        """Test validation fails for data IC without source."""
        processor = InitialConditionProcessor()
        variables = create_test_variables()

        ic = InitialCondition(
            type=InitialConditionType.DATA,
            data_source=None
        )

        errors = processor.validate_initial_conditions(ic, variables)
        assert len(errors) == 1
        assert "requires 'data_source' field" in errors[0]

    def test_validate_constraint_variable_not_found(self):
        """Test validation fails for constraint on non-existent variable."""
        processor = InitialConditionProcessor()
        variables = create_test_variables()

        constraint = FieldConstraint(variable="NONEXISTENT", min_value=0.0)
        processor.add_constraint(constraint)

        ic = InitialCondition(type=InitialConditionType.CONSTANT, value=1e-9)

        errors = processor.validate_initial_conditions(ic, variables)
        assert len(errors) == 1
        assert "not found in model state variables" in errors[0]

    def test_setup_constant_initial_fields(self):
        """Test setting up constant initial fields."""
        processor = InitialConditionProcessor()
        variables = create_test_variables()

        ic = InitialCondition(
            type=InitialConditionType.CONSTANT,
            value=2e-9
        )

        field_values = processor.setup_initial_fields(ic, variables)

        # Should have values for all state variables
        assert "O3" in field_values
        assert "NO" in field_values
        assert "NO2" in field_values
        assert "T" not in field_values  # parameter, not state

        # All should have the constant value
        assert field_values["O3"] == 2e-9
        assert field_values["NO"] == 2e-9
        assert field_values["NO2"] == 2e-9

    def test_setup_with_defaults(self):
        """Test field setup uses default values when appropriate."""
        processor = InitialConditionProcessor()
        variables = create_test_variables()

        # Remove default for one variable to test fallback
        variables["NO"].default = None

        ic = InitialCondition(
            type=InitialConditionType.CONSTANT,
            value=2e-9
        )

        field_values = processor.setup_initial_fields(ic, variables)

        # All should have the constant value (overrides defaults)
        assert field_values["O3"] == 2e-9
        assert field_values["NO"] == 2e-9
        assert field_values["NO2"] == 2e-9

    def test_constraint_clamping(self):
        """Test constraint clamping functionality."""
        processor = InitialConditionProcessor()

        # Add constraint with bounds
        constraint = FieldConstraint(
            variable="O3",
            min_value=1e-8,
            max_value=1e-6,
            operator=ConstraintOperator.CLAMP
        )
        processor.add_constraint(constraint)

        # Test clamping to minimum
        field_values = {"O3": 1e-10}  # Below minimum
        result = processor.apply_constraints(field_values)
        assert result["O3"] == 1e-8

        # Test clamping to maximum
        field_values = {"O3": 1e-5}  # Above maximum
        result = processor.apply_constraints(field_values)
        assert result["O3"] == 1e-6

        # Test value within bounds
        field_values = {"O3": 5e-8}  # Within bounds
        result = processor.apply_constraints(field_values)
        assert result["O3"] == 5e-8

    def test_constraint_error_operator(self):
        """Test constraint error operator raises exception."""
        processor = InitialConditionProcessor()

        constraint = FieldConstraint(
            variable="O3",
            min_value=1e-8,
            operator=ConstraintOperator.ERROR
        )
        processor.add_constraint(constraint)

        field_values = {"O3": 1e-10}  # Below minimum

        with pytest.raises(InitialConditionSetupError):
            processor.apply_constraints(field_values)

    def test_constraint_disabled(self):
        """Test constraints are ignored when disabled."""
        config = InitialConditionConfig(enforce_constraints=False)
        processor = InitialConditionProcessor(config)

        constraint = FieldConstraint(
            variable="O3",
            min_value=1e-8,
            operator=ConstraintOperator.ERROR
        )
        processor.add_constraint(constraint)

        field_values = {"O3": 1e-10}  # Below minimum
        result = processor.apply_constraints(field_values)

        # Should not be modified since constraints are disabled
        assert result["O3"] == 1e-10

    def test_extract_constant_value_numeric(self):
        """Test extracting constant value from numeric input."""
        processor = InitialConditionProcessor()

        assert processor._extract_constant_value(1.5) == 1.5
        assert processor._extract_constant_value(42) == 42.0
        assert processor._extract_constant_value(None) == 0.0

    def test_extract_constant_value_expression(self):
        """Test extracting constant value from expression."""
        processor = InitialConditionProcessor()

        # Simple constant expression
        expr = {"op": "+", "args": [1, 2]}
        # This would require proper expression evaluation
        # For now, it should fall back to default
        result = processor._extract_constant_value(expr)
        assert result == 0.0  # fallback value


class TestHighLevelFunctions:
    """Test high-level convenience functions."""

    def test_setup_initial_conditions_success(self):
        """Test successful initial condition setup."""
        variables = create_test_variables()
        ic = InitialCondition(type=InitialConditionType.CONSTANT, value=1e-9)

        field_values, warnings = setup_initial_conditions(ic, variables)

        assert len(field_values) == 3  # Three state variables
        assert field_values["O3"] == 1e-9
        assert field_values["NO"] == 1e-9
        assert field_values["NO2"] == 1e-9

    def test_setup_initial_conditions_with_constraints(self):
        """Test setup with atmospheric constraints."""
        variables = create_test_variables()
        ic = InitialCondition(type=InitialConditionType.CONSTANT, value=1e-2)  # Very high
        constraints = create_atmospheric_constraints()

        field_values, warnings = setup_initial_conditions(ic, variables, constraints=constraints)

        # O3 should be clamped to maximum
        assert field_values["O3"] == 1e-3  # max from atmospheric constraints
        # NO should be clamped to maximum
        assert field_values["NO"] == 1e-6   # max from atmospheric constraints
        # NO2 should be clamped to maximum
        assert field_values["NO2"] == 1e-6  # max from atmospheric constraints

    def test_create_atmospheric_constraints(self):
        """Test creating standard atmospheric constraints."""
        constraints = create_atmospheric_constraints()

        assert len(constraints) == 3

        # Check O3 constraint
        o3_constraint = next(c for c in constraints if c.variable == "O3")
        assert o3_constraint.min_value == 0.0
        assert o3_constraint.max_value == 1e-3
        assert o3_constraint.units == "mol/mol"

        # Check NO constraint
        no_constraint = next(c for c in constraints if c.variable == "NO")
        assert no_constraint.min_value == 0.0
        assert no_constraint.max_value == 1e-6

        # Check NO2 constraint
        no2_constraint = next(c for c in constraints if c.variable == "NO2")
        assert no2_constraint.min_value == 0.0
        assert no2_constraint.max_value == 1e-6


class TestFieldConstraint:
    """Test FieldConstraint class."""

    def test_field_constraint_creation(self):
        """Test creating field constraint with defaults."""
        constraint = FieldConstraint(variable="test_var")

        assert constraint.variable == "test_var"
        assert constraint.min_value is None
        assert constraint.max_value is None
        assert constraint.units is None
        assert constraint.operator == ConstraintOperator.CLAMP
        assert constraint.description is None

    def test_field_constraint_full_specification(self):
        """Test creating fully specified field constraint."""
        constraint = FieldConstraint(
            variable="O3",
            min_value=0.0,
            max_value=1e-3,
            units="mol/mol",
            operator=ConstraintOperator.ERROR,
            description="Ozone bounds"
        )

        assert constraint.variable == "O3"
        assert constraint.min_value == 0.0
        assert constraint.max_value == 1e-3
        assert constraint.units == "mol/mol"
        assert constraint.operator == ConstraintOperator.ERROR
        assert constraint.description == "Ozone bounds"


class TestConstraintOperator:
    """Test ConstraintOperator enum."""

    def test_constraint_operator_values(self):
        """Test constraint operator enum values."""
        assert ConstraintOperator.CLAMP.value == "clamp"
        assert ConstraintOperator.WARN.value == "warn"
        assert ConstraintOperator.ERROR.value == "error"


if __name__ == "__main__":
    pytest.main([__file__])