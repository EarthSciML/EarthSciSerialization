#!/usr/bin/env python3
"""Simple test of initial conditions setup system."""

import sys
import os

# Add the package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/esm_format/src'))

try:
    from esm_format import (
        InitialCondition,
        InitialConditionType,
        ModelVariable,
        InitialConditionProcessor,
        setup_initial_conditions,
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

    # Test high-level function
    field_values2, warnings = setup_initial_conditions(ic, variables)

    if field_values == field_values2:
        print("✓ High-level function produces same results")
    else:
        print(f"✗ High-level function mismatch")
        sys.exit(1)

    # Test atmospheric constraints
    constraints = create_atmospheric_constraints()

    if len(constraints) == 3:
        print("✓ Created atmospheric constraints")
    else:
        print(f"✗ Expected 3 constraints, got {len(constraints)}")
        sys.exit(1)

    print("🎉 All tests passed! Initial condition setup system is working.")

except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)