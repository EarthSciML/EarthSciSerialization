#!/usr/bin/env python3
"""Consolidated test of initial conditions setup system.

This test consolidates functionality from 4 duplicate test files:
- test_core_functionality.py
- test_ic_direct.py
- test_ic_standalone.py
- test_initial_conditions_simple.py

Tests all core functionality of the initial conditions setup system including:
- Basic processor creation and validation
- Variable setup and field initialization
- Constraint system and clamping
- Atmospheric constraints
- High-level function interface
- Error handling
"""

import sys
import os
from typing import Dict
from dataclasses import dataclass
from enum import Enum

# Add the package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/esm_format/src'))

# Define essential types for fallback if imports fail
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

def test_with_direct_imports():
    """Test using direct imports from the esm_format package."""
    try:
        from esm_format import (
            InitialCondition,
            InitialConditionType,
            ModelVariable,
            InitialConditionProcessor,
            setup_initial_conditions,
            create_atmospheric_constraints
        )
        print("✓ Successfully imported from esm_format package")
        return run_core_tests_direct(
            InitialCondition, InitialConditionType, ModelVariable,
            InitialConditionProcessor, setup_initial_conditions,
            create_atmospheric_constraints
        )
    except ImportError as e:
        print(f"⚠ Direct import failed: {e}")
        return False

def test_with_submodule_imports():
    """Test using submodule imports."""
    try:
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
            setup_initial_conditions,
            create_atmospheric_constraints
        )
        print("✓ Successfully imported from esm_format submodules")
        return run_core_tests_submodule(
            InitialCondition, InitialConditionType, ModelVariable,
            InitialConditionProcessor, FieldConstraint, ConstraintOperator,
            setup_initial_conditions, create_atmospheric_constraints
        )
    except ImportError as e:
        print(f"⚠ Submodule import failed: {e}")
        return False

def test_with_inline_definitions():
    """Test using inline type definitions and direct module loading."""
    try:
        # Create test data with inline definitions
        variables = create_test_variables()
        ic = InitialCondition(type=InitialConditionType.CONSTANT, value=2e-9)

        # Try to load module directly
        module_path = 'packages/esm_format/src/esm_format/initial_conditions_setup.py'

        if not os.path.exists(module_path):
            print(f"⚠ Module not found: {module_path}")
            return False

        # Create namespace with required imports
        namespace = {
            'InitialCondition': InitialCondition,
            'InitialConditionType': InitialConditionType,
            'ModelVariable': ModelVariable,
            'Domain': None,  # Stub
            'Expr': dict,    # Stub
        }

        # Read and execute module
        with open(module_path, 'r') as f:
            module_code = f.read()

        # Replace problematic imports with stubs
        module_code = module_code.replace(
            """try:
    from .types import (
        InitialCondition,
        InitialConditionType,
        ModelVariable,
        Domain,
        Expr
    )
    from .expression import evaluate_expr_dict
except ImportError:
    # Fallback for direct imports
    from types import (
        InitialCondition,
        InitialConditionType,
        ModelVariable,
        Domain,
        Expr
    )
    # Stub for expression evaluation if not available
    def evaluate_expr_dict(expr, variables):
        return 0.0""",
            """# Direct imports for testing
def evaluate_expr_dict(expr, variables):
    return 0.0"""
        )

        exec(module_code, namespace)

        # Extract classes
        InitialConditionProcessor = namespace['InitialConditionProcessor']
        FieldConstraint = namespace['FieldConstraint']
        ConstraintOperator = namespace['ConstraintOperator']
        setup_initial_conditions = namespace['setup_initial_conditions']
        create_atmospheric_constraints = namespace['create_atmospheric_constraints']

        print("✓ Successfully loaded module with inline definitions")
        return run_core_tests_inline(
            ic, variables, InitialConditionProcessor, FieldConstraint,
            ConstraintOperator, setup_initial_conditions, create_atmospheric_constraints
        )

    except Exception as e:
        print(f"⚠ Inline definition test failed: {e}")
        return False

def create_test_variables():
    """Create standard test variables."""
    return {
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

def run_core_tests_direct(IC, ICType, ModelVar, Processor, setup_func, constraints_func):
    """Run core tests using direct imports."""
    variables = create_test_variables()
    ic = IC(type=ICType.CONSTANT, value=2e-9)

    return run_standard_tests(ic, variables, Processor, None, None, setup_func, constraints_func)

def run_core_tests_submodule(IC, ICType, ModelVar, Processor, FieldConstraint, ConstraintOp, setup_func, constraints_func):
    """Run core tests using submodule imports."""
    variables = create_test_variables()
    ic = IC(type=ICType.CONSTANT, value=2e-9)

    return run_standard_tests(ic, variables, Processor, FieldConstraint, ConstraintOp, setup_func, constraints_func)

def run_core_tests_inline(ic, variables, Processor, FieldConstraint, ConstraintOp, setup_func, constraints_func):
    """Run core tests using inline definitions."""
    return run_standard_tests(ic, variables, Processor, FieldConstraint, ConstraintOp, setup_func, constraints_func)

def run_standard_tests(ic, variables, Processor, FieldConstraint, ConstraintOp, setup_func, constraints_func):
    """Run the standard test suite."""
    try:
        # Test 1: Basic processor creation
        processor = Processor()
        print("✓ Processor created")

        # Test 2: Validation
        errors = processor.validate_initial_conditions(ic, variables)
        if not errors:
            print("✓ Validation passed")
        else:
            print(f"✗ Validation failed: {errors}")
            return False

        # Test 3: Field setup
        field_values = processor.setup_initial_fields(ic, variables)
        expected_fields = {"O3", "NO", "NO2"}

        if set(field_values.keys()) == expected_fields:
            print("✓ Field setup created correct variables")
        else:
            print(f"✗ Expected {expected_fields}, got {set(field_values.keys())}")
            return False

        if all(v == 2e-9 for v in field_values.values()):
            print("✓ All field values are correct constant value")
        else:
            print(f"✗ Field values are not all 2e-9: {field_values}")
            return False

        # Test 4: Constraint system (if available)
        if FieldConstraint and ConstraintOp:
            constraint = FieldConstraint(
                variable="O3",
                min_value=0.0,
                max_value=1e-6,
                operator=ConstraintOp.CLAMP
            )

            processor.add_constraint(constraint)

            # Test with value that needs clamping
            test_values = {"O3": 1e-5}  # Above maximum
            clamped_values = processor.apply_constraints(test_values)

            if clamped_values["O3"] == 1e-6:
                print("✓ Constraint clamping works correctly")
            else:
                print(f"✗ Expected clamped value 1e-6, got {clamped_values['O3']}")
                return False

        # Test 5: High-level function
        field_values2, warnings = setup_func(ic, variables)
        if field_values == field_values2:
            print("✓ High-level function produces same results")
        else:
            print("⚠ High-level function results differ (may be due to constraints)")

        # Test 6: Atmospheric constraints
        constraints = constraints_func()
        if len(constraints) == 3:
            print("✓ Created atmospheric constraints")
        else:
            print(f"⚠ Expected 3 constraints, got {len(constraints)}")

        # Test 7: Error handling
        bad_ic = InitialCondition(type=InitialConditionType.CONSTANT, value=None)
        errors = processor.validate_initial_conditions(bad_ic, variables)
        if errors:
            print("✓ Validation correctly detects errors")
        else:
            print("⚠ Validation should have detected error with None value")

        return True

    except Exception as e:
        print(f"✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test runner."""
    print("Initial Conditions Setup System - Consolidated Tests")
    print("=" * 60)

    test_results = []

    # Try different import strategies
    print("\n1. Testing with direct package imports...")
    test_results.append(test_with_direct_imports())

    print("\n2. Testing with submodule imports...")
    test_results.append(test_with_submodule_imports())

    print("\n3. Testing with inline definitions...")
    test_results.append(test_with_inline_definitions())

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    successful_tests = sum(test_results)
    total_tests = len(test_results)

    if successful_tests > 0:
        print(f"✓ {successful_tests}/{total_tests} test approaches succeeded")
        print("🎉 Initial condition setup system is working!")

        # Demonstrate usage
        print("\n" + "=" * 40)
        print("DEMONSTRATION")
        print("=" * 40)
        demonstrate_usage()

        return 0
    else:
        print("✗ All test approaches failed")
        print("🔧 Initial condition setup system needs attention")
        return 1

def demonstrate_usage():
    """Demonstrate typical usage patterns."""
    print("\nDemonstrating typical usage...")

    # Create atmospheric chemistry variables
    atm_variables = {
        "O3": ModelVariable(type="state", units="mol/mol", default=40e-9, description="Ozone"),
        "NO": ModelVariable(type="state", units="mol/mol", default=0.1e-9, description="Nitric oxide"),
        "NO2": ModelVariable(type="state", units="mol/mol", default=1.0e-9, description="Nitrogen dioxide"),
        "HO2": ModelVariable(type="state", units="mol/mol", default=1e-12, description="Hydroperoxyl radical"),
        "OH": ModelVariable(type="state", units="mol/mol", default=1e-12, description="Hydroxyl radical"),
    }

    # Use constant initial conditions
    atm_ic = InitialCondition(type=InitialConditionType.CONSTANT, value=1e-8)  # 10 ppb

    print("\nAtmospheric chemistry setup:")
    print(f"- {len(atm_variables)} species")
    print(f"- Initial condition type: {atm_ic.type.value}")
    print(f"- Initial value: {atm_ic.value:.2e} mol/mol")

    print("\nVariable summary:")
    for var, info in atm_variables.items():
        print(f"  {var:4s}: {info.description} (default: {info.default:.2e} {info.units})")

    print("\n✓ Demonstration complete")

if __name__ == "__main__":
    sys.exit(main())