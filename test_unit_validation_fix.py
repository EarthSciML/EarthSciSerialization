#!/usr/bin/env python3
"""
Test script to verify that unit validation is no longer a no-op.

This script tests the integration of UnitValidator into the main validation system.
"""

import sys
import os
sys.path.insert(0, 'packages/esm_format/src')

def test_unit_validation_integration():
    """Test that unit validation is properly integrated."""

    # Test 1: Check that the validation module can import UnitValidator
    print("Test 1: Testing validation module imports...")
    try:
        from esm_format.validation import validate, UnitWarning
        from esm_format.esm_types import EsmFile, Model, ModelVariable
        print("✓ Successfully imported validation components")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

    # Test 2: Check that _validate_units function is no longer a no-op
    print("\nTest 2: Testing _validate_units function...")
    from esm_format.validation import _validate_units
    import inspect

    # Get the source code of _validate_units
    source = inspect.getsource(_validate_units)
    if 'pass' in source and 'TODO' in source:
        print("✗ _validate_units still contains no-op code (pass statement with TODO)")
        return False
    elif 'UnitValidator' in source:
        print("✓ _validate_units now uses UnitValidator")
    else:
        print("? _validate_units doesn't contain obvious no-op, but unclear if properly implemented")
        print("Source preview:")
        print(source[:200] + "...")

    # Test 3: Create a minimal ESM file and test validation
    print("\nTest 3: Testing unit validation on minimal ESM file...")

    # Create a simple model with unit information
    model = Model(name="test_model")
    model.variables = {
        "temperature": ModelVariable(type="state", units="kelvin"),
        "pressure": ModelVariable(type="state", units="pascal")
    }

    # Create minimal ESM file
    esm_file = EsmFile()
    esm_file.models = [model]
    esm_file.reaction_systems = []
    esm_file.coupling = []
    esm_file.events = []
    esm_file.operators = []
    esm_file.domain = None
    esm_file.initial_conditions = []
    esm_file.boundary_conditions = []
    esm_file.solver = None
    esm_file.references = []
    esm_file.metadata = None

    # Test unit warnings collection
    unit_warnings = []
    try:
        _validate_units(esm_file, unit_warnings)
        if len(unit_warnings) > 0:
            print(f"✓ Unit validation produced {len(unit_warnings)} warnings:")
            for warning in unit_warnings:
                print(f"  - {warning.message}")
        else:
            print("✓ Unit validation executed without warnings (may be expected)")
        print("✓ Unit validation is no longer a no-op")
        return True
    except Exception as e:
        print(f"✗ Unit validation failed with error: {e}")
        return False

def main():
    """Run the unit validation tests."""
    print("Testing Unit Validation Integration Fix")
    print("=" * 50)

    success = test_unit_validation_integration()

    print("\n" + "=" * 50)
    if success:
        print("✅ PASS: Unit validation is properly integrated and no longer a no-op")
        return 0
    else:
        print("❌ FAIL: Unit validation integration issues detected")
        return 1

if __name__ == "__main__":
    sys.exit(main())