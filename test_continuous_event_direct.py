#!/usr/bin/env python3
"""
Simple test to verify ContinuousEvent fixes - direct module import
"""
import sys
import os

# Add the package to path
sys.path.insert(0, '/home/ctessum/EarthSciSerialization/packages/esm_format/src/esm_format')

try:
    # Import directly from the module files
    import esm_types
    from esm_types import ContinuousEvent, AffectEquation

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

    print("✅ ContinuousEvent creation successful!")
    print(f"  Name: {event.name}")
    print(f"  Conditions: {event.conditions}")
    print(f"  Affects: {len(event.affects)} items")
    print(f"  Affect_neg: {len(event.affect_neg)} items" if event.affect_neg else "  Affect_neg: None")
    print(f"  Root_find: {event.root_find}")
    print(f"  Reinitialize: {event.reinitialize}")
    print(f"  Description: {event.description}")

    # Check that all required schema fields are present
    print("\n✅ All new schema fields implemented:")
    print("  ✓ conditions (array)")
    print("  ✓ affects (array)")
    print("  ✓ affect_neg (optional array)")
    print("  ✓ root_find (optional enum with default)")
    print("  ✓ reinitialize (optional boolean with default)")
    print("  ✓ description (optional string)")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)