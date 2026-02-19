#!/usr/bin/env python3
"""
Simple test to verify ContinuousEvent fixes
"""
import sys
import os

# Add the package to path
sys.path.insert(0, '/home/ctessum/EarthSciSerialization/packages/esm_format/src')

try:
    from esm_format import ContinuousEvent, AffectEquation

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
    from esm_format import save
    from esm_format import EsmFile, Metadata

    esm_file = EsmFile(
        version="0.1.0",
        metadata=Metadata(title="Test"),
        events=[event]
    )

    # Try saving to test serialization
    save(esm_file, "/tmp/test_continuous_event.json")
    print("✓ Serialization successful")

    # Test loading back
    from esm_format import load
    loaded_esm = load("/tmp/test_continuous_event.json")

    loaded_event = loaded_esm.events[0]
    print("✓ Parsing successful")
    print(f"  Loaded conditions: {loaded_event.conditions}")
    print(f"  Loaded affect_neg: {len(loaded_event.affect_neg)} items" if loaded_event.affect_neg else "  Loaded affect_neg: None")
    print(f"  Loaded root_find: {loaded_event.root_find}")
    print(f"  Loaded reinitialize: {loaded_event.reinitialize}")

    print("\n✅ All ContinuousEvent fixes working correctly!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)