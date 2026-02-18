#!/usr/bin/env python3
"""
Simple test to verify ContinuousEvent fixes - minimal imports
"""
import sys
import os

# Add the package to path
sys.path.insert(0, '/home/ctessum/EarthSciSerialization/packages/esm_format/src')

try:
    # Import directly from esm_types to avoid other dependencies
    from esm_format.esm_types import ContinuousEvent, AffectEquation
    from esm_format.serialize import _serialize_continuous_event
    from esm_format.parse import _parse_continuous_event

    # Test creating a ContinuousEvent with new fields
    affect = AffectEquation(lhs="x", rhs="0.5")
    affect_neg = AffectEquation(lhs="y", rhs="1.0")

    event = ContinuousEvent(
        name="test_event",
        conditions=["x > 5.0"],  # Now an array
        affects=[affect],
        affect_neg=[affect_neg],  # New field
        root_find="right",  # New field
        reinitialize=True,  # New field
        description="Test continuous event"  # New field
    )

    print("✓ ContinuousEvent creation successful")
    print(f"  Name: {event.name}")
    print(f"  Conditions: {event.conditions}")
    print(f"  Affects: {len(event.affects)} items")
    print(f"  Affect_neg: {len(event.affect_neg)} items" if event.affect_neg else "  Affect_neg: None")
    print(f"  Root_find: {event.root_find}")
    print(f"  Reinitialize: {event.reinitialize}")
    print(f"  Description: {event.description}")

    # Test serialization
    serialized = _serialize_continuous_event(event)
    print(f"✓ Serialization successful: {serialized}")

    # Test parsing back
    parsed_event = _parse_continuous_event(serialized)
    print(f"✓ Parsing successful")
    print(f"  Parsed conditions: {parsed_event.conditions}")
    print(f"  Parsed affect_neg: {len(parsed_event.affect_neg)} items" if parsed_event.affect_neg else "  Parsed affect_neg: None")
    print(f"  Parsed root_find: {parsed_event.root_find}")
    print(f"  Parsed reinitialize: {parsed_event.reinitialize}")

    print("\n✅ All ContinuousEvent fixes working correctly!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)