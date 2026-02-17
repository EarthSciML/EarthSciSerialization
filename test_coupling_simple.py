#!/usr/bin/env python3
"""
Simple test script to verify the Python coupling type fixes without dependencies.
"""
import json
import sys
import os
from pathlib import Path

# Add the package to Python path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root / 'packages' / 'esm_format' / 'src'))

# Direct import from the types module
sys.path.insert(0, str(repo_root / 'packages' / 'esm_format' / 'src' / 'esm_format'))
from esm_types import CouplingType, CouplingEntry

def main():
    """Test the coupling type fixes."""
    print("Testing CouplingType enum:")
    for ct in CouplingType:
        print(f"  {ct.name} = '{ct.value}'")

    print(f"\n✅ Found {len(CouplingType)} coupling types")

    # Check that we have the right enum values
    expected_types = {
        'operator_compose', 'couple2', 'variable_map',
        'operator_apply', 'callback', 'event'
    }
    actual_types = {ct.value for ct in CouplingType}

    if expected_types == actual_types:
        print("✅ All expected coupling types are present")
    else:
        print(f"❌ Missing types: {expected_types - actual_types}")
        print(f"❌ Extra types: {actual_types - expected_types}")
        return False

    # Test creating coupling entries
    print("\nTesting CouplingEntry creation:")

    test_cases = [
        {
            'type': CouplingType.OPERATOR_COMPOSE,
            'systems': ['Model1', 'Model2'],
            'description': 'Test operator compose'
        },
        {
            'type': CouplingType.VARIABLE_MAP,
            'from_var': 'source.var',
            'to_var': 'target.var',
            'transform': 'identity'
        },
        {
            'type': CouplingType.CALLBACK,
            'callback_id': 'test_callback',
            'config': {'frequency': 3600}
        }
    ]

    for i, case in enumerate(test_cases):
        try:
            coupling = CouplingEntry(coupling_type=case['type'])
            for key, value in case.items():
                if key != 'type':
                    setattr(coupling, key, value)
            print(f"✅ Created {case['type'].value} coupling")
        except Exception as e:
            print(f"❌ Failed to create {case['type'].value}: {e}")
            return False

    print("\n🎉 All coupling type tests passed!")

    # Test with actual ESM file data if available
    test_file = repo_root / "tests" / "coupling" / "complete_coupling_types.esm"
    if test_file.exists():
        print(f"\nTesting with actual ESM file: {test_file}")
        try:
            with open(test_file) as f:
                data = json.load(f)

            coupling_entries = data.get('coupling', [])
            print(f"Found {len(coupling_entries)} coupling entries in test file")

            type_mapping = {
                'operator_compose': CouplingType.OPERATOR_COMPOSE,
                'couple2': CouplingType.COUPLE2,
                'variable_map': CouplingType.VARIABLE_MAP,
                'operator_apply': CouplingType.OPERATOR_APPLY,
                'callback': CouplingType.CALLBACK,
                'event': CouplingType.EVENT,
            }

            for i, entry in enumerate(coupling_entries):
                schema_type = entry.get('type')
                if schema_type in type_mapping:
                    enum_type = type_mapping[schema_type]
                    print(f"✅ Entry {i}: {schema_type} -> {enum_type.value}")
                else:
                    print(f"❌ Entry {i}: Unknown type {schema_type}")
                    return False

            print("✅ All entries map to valid coupling types!")

        except Exception as e:
            print(f"❌ Error testing with ESM file: {e}")
            return False
    else:
        print(f"\nTest file {test_file} not found, skipping file test")

    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Python coupling type bug is FIXED!")
    else:
        print("\n❌ Python coupling type bug still exists")
    sys.exit(0 if success else 1)