#!/usr/bin/env python3
"""Test that the updated schema validates CouplingEvent with functional_affect."""

import json
import jsonschema
import sys
import os

def validate_test_file(schema_file, test_file):
    """Validate a test ESM file against the schema."""
    try:
        # Load schema
        with open(schema_file, 'r') as f:
            schema = json.load(f)

        # Load test file
        with open(test_file, 'r') as f:
            test_data = json.load(f)

        # Validate
        jsonschema.validate(test_data, schema)
        print(f"✓ {test_file} validates successfully against schema")
        return True

    except jsonschema.ValidationError as e:
        print(f"✗ {test_file} validation failed:")
        print(f"  Error: {e.message}")
        print(f"  Path: {' > '.join(str(p) for p in e.absolute_path)}")
        return False
    except Exception as e:
        print(f"✗ {test_file} error: {e}")
        return False

if __name__ == "__main__":
    schema_file = "esm-schema.json"
    test_files = [
        "test_coupling_event_functional_affect.esm",
        "test_coupling_continuous_functional_affect.esm"
    ]

    success = True
    for test_file in test_files:
        if os.path.exists(test_file):
            if not validate_test_file(schema_file, test_file):
                success = False
        else:
            print(f"✗ Test file {test_file} not found")
            success = False

    if success:
        print("\nAll tests passed! ✓")
        sys.exit(0)
    else:
        print("\nSome tests failed! ✗")
        sys.exit(1)