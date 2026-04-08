#!/usr/bin/env python3
"""Comprehensive validation test for CouplingEvent functional_affect support."""

import json
import jsonschema
import sys

def validate_esm(esm_data):
    """Validate ESM data against schema."""
    with open('esm-schema.json', 'r') as f:
        schema = json.load(f)

    try:
        jsonschema.validate(esm_data, schema)
        return True, None
    except jsonschema.ValidationError as e:
        return False, e.message

def create_base_esm():
    """Create a base ESM structure."""
    return {
        "esm": "0.1.0",
        "metadata": {"name": "test"},
        "models": {
            "TestModel": {
                "variables": {"x": {"type": "state", "default": 1.0}},
                "equations": []
            }
        }
    }

def test_case(name, esm_data, should_pass=True):
    """Test a specific ESM case."""
    valid, error = validate_esm(esm_data)

    if should_pass:
        if valid:
            print(f"✓ {name}: Passed as expected")
            return True
        else:
            print(f"✗ {name}: Failed unexpectedly - {error}")
            return False
    else:
        if not valid:
            print(f"✓ {name}: Correctly rejected - {error}")
            return True
        else:
            print(f"✗ {name}: Should have failed but passed")
            return False

def main():
    """Run comprehensive validation tests."""
    print("Running comprehensive CouplingEvent functional_affect validation tests...\n")

    success_count = 0
    total_count = 0

    # Test 1: Valid discrete event with functional_affect
    base = create_base_esm()
    base["coupling"] = [{
        "type": "event",
        "event_type": "discrete",
        "name": "test_discrete",
        "trigger": {
            "type": "condition",
            "expression": {"op": ">", "args": ["TestModel.x", 1.0]}
        },
        "functional_affect": {
            "handler_id": "test_handler",
            "read_vars": ["TestModel.x"],
            "read_params": [],
            "modified_params": []
        }
    }]

    total_count += 1
    if test_case("Discrete event with functional_affect", base, True):
        success_count += 1

    # Test 2: Valid continuous event with functional_affect
    base = create_base_esm()
    base["coupling"] = [{
        "type": "event",
        "event_type": "continuous",
        "name": "test_continuous",
        "conditions": [{"op": "-", "args": ["TestModel.x", 0.5]}],
        "functional_affect": {
            "handler_id": "test_handler",
            "read_vars": ["TestModel.x"],
            "read_params": [],
            "modified_params": []
        }
    }]

    total_count += 1
    if test_case("Continuous event with functional_affect", base, True):
        success_count += 1

    # Test 3: Valid discrete event with affects (traditional)
    base = create_base_esm()
    base["coupling"] = [{
        "type": "event",
        "event_type": "discrete",
        "name": "test_affects",
        "trigger": {
            "type": "condition",
            "expression": {"op": ">", "args": ["TestModel.x", 1.0]}
        },
        "affects": [{"lhs": "TestModel.x", "rhs": 0.0}]
    }]

    total_count += 1
    if test_case("Discrete event with affects", base, True):
        success_count += 1

    # Test 4: Invalid - both affects and functional_affect (should fail)
    base = create_base_esm()
    base["coupling"] = [{
        "type": "event",
        "event_type": "discrete",
        "name": "test_both",
        "trigger": {
            "type": "condition",
            "expression": {"op": ">", "args": ["TestModel.x", 1.0]}
        },
        "affects": [{"lhs": "TestModel.x", "rhs": 0.0}],
        "functional_affect": {
            "handler_id": "test_handler",
            "read_vars": ["TestModel.x"],
            "read_params": [],
            "modified_params": []
        }
    }]

    total_count += 1
    if test_case("Event with both affects and functional_affect", base, False):
        success_count += 1

    # Test 5: Invalid - neither affects nor functional_affect (should fail)
    base = create_base_esm()
    base["coupling"] = [{
        "type": "event",
        "event_type": "discrete",
        "name": "test_neither",
        "trigger": {
            "type": "condition",
            "expression": {"op": ">", "args": ["TestModel.x", 1.0]}
        }
    }]

    total_count += 1
    if test_case("Event with neither affects nor functional_affect", base, False):
        success_count += 1

    # Test 6: Invalid - discrete event missing trigger (should fail)
    base = create_base_esm()
    base["coupling"] = [{
        "type": "event",
        "event_type": "discrete",
        "name": "test_no_trigger",
        "functional_affect": {
            "handler_id": "test_handler",
            "read_vars": ["TestModel.x"],
            "read_params": [],
            "modified_params": []
        }
    }]

    total_count += 1
    if test_case("Discrete event missing trigger", base, False):
        success_count += 1

    # Test 7: Invalid - continuous event missing conditions (should fail)
    base = create_base_esm()
    base["coupling"] = [{
        "type": "event",
        "event_type": "continuous",
        "name": "test_no_conditions",
        "functional_affect": {
            "handler_id": "test_handler",
            "read_vars": ["TestModel.x"],
            "read_params": [],
            "modified_params": []
        }
    }]

    total_count += 1
    if test_case("Continuous event missing conditions", base, False):
        success_count += 1

    print(f"\n{'='*50}")
    print(f"Results: {success_count}/{total_count} tests passed")

    if success_count == total_count:
        print("🎉 All tests passed! CouplingEvent functional_affect support is working correctly.")
        return 0
    else:
        print("❌ Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())