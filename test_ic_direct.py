#!/usr/bin/env python3
"""Direct test of initial conditions setup system."""

import sys
import os
from typing import Dict
from dataclasses import dataclass
from enum import Enum

# Add the package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/esm_format/src'))

# Import the essential types directly
class InitialConditionType(Enum):
    """Types of initial conditions."""
    CONSTANT = "constant"
    FUNCTION = "function"
    DATA = "data"

@dataclass
class InitialCondition:
    """Initial condition specification."""
    type: InitialConditionType
    value: float = None
    function: str = None
    data_source: str = None

@dataclass
class ModelVariable:
    """Model variable specification."""
    type: str
    units: str = None
    default: float = None
    description: str = None

# Import the initial conditions setup module directly
try:
    from esm_format.initial_conditions_setup import (
        InitialConditionProcessor,
        InitialConditionConfig,
        FieldConstraint,
        ConstraintOperator,
        create_atmospheric_constraints
    )

    print("✓ Successfully imported initial condition setup system")

    # Create test variables
    variables = {
        "O3": ModelVariable(
            type="state",
            units="mol/mol",
            default=1e-8,
            description="Ozone"
        ),
        "NO": ModelVariable(
            type="state",
            units="mol/mol",
            default=1e-10,
            description="Nitric oxide"
        ),
        "NO2": ModelVariable(
            type="state",
            units="mol/mol",
            default=1e-10,
            description="Nitrogen dioxide"
        )
    }

    # Test constant initial conditions
    ic = InitialCondition(
        type=InitialConditionType.CONSTANT,
        value=2e-9
    )

    print("✓ Created test data")

    # Test processor
    processor = InitialConditionProcessor()
    errors = processor.validate_initial_conditions(ic, variables)

    if not errors:
        print("✓ Validation passed")
    else:
        print(f"✗ Validation failed: {errors}")
        sys.exit(1)

    # Test field setup
    field_values = processor.setup_initial_fields(ic, variables)

    expected_fields = {"O3", "NO", "NO2"}
    if set(field_values.keys()) == expected_fields:
        print("✓ Field setup created correct variables")
    else:
        print(f"✗ Expected {expected_fields}, got {set(field_values.keys())}")
        sys.exit(1)

    if all(v == 2e-9 for v in field_values.values()):
        print("✓ All field values are correct constant value")
    else:
        print(f"✗ Field values are not all 2e-9: {field_values}")
        sys.exit(1)

    # Test constraint system
    constraint = FieldConstraint(
        variable="O3",
        min_value=0.0,
        max_value=1e-6,
        operator=ConstraintOperator.CLAMP
    )

    processor.add_constraint(constraint)

    # Test with value that needs clamping
    test_values = {"O3": 1e-5}  # Above maximum
    clamped_values = processor.apply_constraints(test_values)

    if clamped_values["O3"] == 1e-6:
        print("✓ Constraint clamping works correctly")
    else:
        print(f"✗ Expected clamped value 1e-6, got {clamped_values['O3']}")
        sys.exit(1)

    # Test atmospheric constraints
    constraints = create_atmospheric_constraints()

    if len(constraints) == 3:
        print("✓ Created atmospheric constraints")
    else:
        print(f"✗ Expected 3 constraints, got {len(constraints)}")
        sys.exit(1)

    print("🎉 All tests passed! Initial condition setup system is working.")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)