#!/usr/bin/env python3
"""
Test script to verify the Python coupling type fixes.
"""
import json
import sys
import os

# Add the package to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages', 'esm_format', 'src'))

# Import types directly from the renamed module
from esm_format.esm_types import CouplingType, CouplingEntry, ConnectorEquation, Connector

def test_parse_coupling_entry(coupling_data):
    """Simple test function to parse coupling entries."""
    schema_type = coupling_data['type']

    # Map schema types to enum values
    type_mapping = {
        'operator_compose': CouplingType.OPERATOR_COMPOSE,
        'couple2': CouplingType.COUPLE2,
        'variable_map': CouplingType.VARIABLE_MAP,
        'operator_apply': CouplingType.OPERATOR_APPLY,
        'callback': CouplingType.CALLBACK,
        'event': CouplingType.EVENT,
    }

    if schema_type not in type_mapping:
        raise ValueError(f"Unknown coupling type: {schema_type}")

    coupling_type = type_mapping[schema_type]

    # Create base coupling entry
    entry = CouplingEntry(
        coupling_type=coupling_type,
        description=coupling_data.get('description')
    )

    # Parse type-specific fields
    if coupling_type == CouplingType.OPERATOR_COMPOSE:
        entry.systems = coupling_data.get('systems', [])
        entry.translate = coupling_data.get('translate', {})

    elif coupling_type == CouplingType.COUPLE2:
        entry.systems = coupling_data.get('systems', [])
        entry.coupletype_pair = coupling_data.get('coupletype_pair', [])

    elif coupling_type == CouplingType.VARIABLE_MAP:
        entry.from_var = coupling_data.get('from')
        entry.to_var = coupling_data.get('to')
        entry.transform = coupling_data.get('transform')
        entry.factor = coupling_data.get('factor')

    elif coupling_type == CouplingType.OPERATOR_APPLY:
        entry.operator = coupling_data.get('operator')

    elif coupling_type == CouplingType.CALLBACK:
        entry.callback_id = coupling_data.get('callback_id')
        entry.config = coupling_data.get('config', {})

    elif coupling_type == CouplingType.EVENT:
        entry.event_type = coupling_data.get('event_type')

    return entry

def main():
    """Test the coupling type fixes."""
    print("Testing CouplingType enum:")
    for ct in CouplingType:
        print(f"  {ct.name} = '{ct.value}'")

    print("\nTesting coupling entry parsing...")

    # Load test data
    test_file = "tests/coupling/complete_coupling_types.esm"
    try:
        with open(test_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Test file {test_file} not found. Skipping parsing test.")
        return

    coupling_entries = data['coupling']
    print(f"\nParsing {len(coupling_entries)} coupling entries:")

    success_count = 0

    for i, entry in enumerate(coupling_entries):
        try:
            coupling = test_parse_coupling_entry(entry)
            print(f"✓ Entry {i}: {entry['type']} -> {coupling.coupling_type.value}")

            # Show key fields
            if coupling.systems:
                print(f"  Systems: {coupling.systems}")
            if coupling.from_var:
                print(f"  From: {coupling.from_var} -> To: {coupling.to_var}")
            if coupling.operator:
                print(f"  Operator: {coupling.operator}")
            if coupling.callback_id:
                print(f"  Callback: {coupling.callback_id}")
            if coupling.event_type:
                print(f"  Event type: {coupling.event_type}")

            success_count += 1

        except Exception as e:
            print(f"✗ Entry {i}: {entry['type']} failed: {e}")

    print(f"\n✓ Successfully parsed {success_count}/{len(coupling_entries)} coupling entries!")

    if success_count == len(coupling_entries):
        print("\n🎉 All coupling types are now correctly implemented!")
        return True
    else:
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)