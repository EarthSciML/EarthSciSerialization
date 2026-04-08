#!/usr/bin/env python3
"""
Test serialization and parsing of updated ContinuousEvent
"""
import sys
import os

# Add the package to path
sys.path.insert(0, '/home/ctessum/EarthSciSerialization/packages/esm_format/src/esm_format')

try:
    from esm_types import ContinuousEvent, AffectEquation
    import serialize
    import parse
    import json

    # Test creating a ContinuousEvent with all new fields
    affect1 = AffectEquation(lhs="x", rhs="0.5")
    affect2 = AffectEquation(lhs="y", rhs="1.0")
    affect_neg1 = AffectEquation(lhs="z", rhs="2.0")

    event = ContinuousEvent(
        name="full_test_event",
        conditions=["x > 5.0", "y < 3.0"],  # Multiple conditions
        affects=[affect1, affect2],
        affect_neg=[affect_neg1],  # New field
        root_find="all",  # New field
        reinitialize=True,  # New field
        description="Full test continuous event",  # New field
        priority=2
    )

    print("✅ ContinuousEvent created with all fields")

    # Test serialization
    serialized = serialize._serialize_continuous_event(event)
    print(f"✅ Serialization successful")
    print(f"Serialized JSON: {json.dumps(serialized, indent=2)}")

    # Test parsing back
    parsed_event = parse._parse_continuous_event(serialized)
    print(f"✅ Parsing successful")

    # Verify all fields were preserved
    print("\n🔍 Verification:")
    print(f"  Name: {parsed_event.name} ({'✓' if parsed_event.name == event.name else '❌'})")
    print(f"  Conditions: {len(parsed_event.conditions)} items ({'✓' if len(parsed_event.conditions) == 2 else '❌'})")
    print(f"  Affects: {len(parsed_event.affects)} items ({'✓' if len(parsed_event.affects) == 2 else '❌'})")
    print(f"  Affect_neg: {len(parsed_event.affect_neg)} items ({'✓' if parsed_event.affect_neg and len(parsed_event.affect_neg) == 1 else '❌'})")
    print(f"  Root_find: {parsed_event.root_find} ({'✓' if parsed_event.root_find == 'all' else '❌'})")
    print(f"  Reinitialize: {parsed_event.reinitialize} ({'✓' if parsed_event.reinitialize == True else '❌'})")
    print(f"  Description: {parsed_event.description} ({'✓' if parsed_event.description == event.description else '❌'})")
    print(f"  Priority: {parsed_event.priority} ({'✓' if parsed_event.priority == 2 else '❌'})")

    # Test with minimal fields (defaults)
    minimal_event = ContinuousEvent(
        name="minimal",
        conditions=["t > 0"],
        affects=[]
    )

    print("\n✅ Testing with minimal fields (using defaults)")
    minimal_serialized = serialize._serialize_continuous_event(minimal_event)
    minimal_parsed = parse._parse_continuous_event(minimal_serialized)

    print(f"  Minimal root_find: {minimal_parsed.root_find} ({'✓' if minimal_parsed.root_find == 'left' else '❌'})")
    print(f"  Minimal reinitialize: {minimal_parsed.reinitialize} ({'✓' if minimal_parsed.reinitialize == False else '❌'})")
    print(f"  Minimal affect_neg: {minimal_parsed.affect_neg} ({'✓' if minimal_parsed.affect_neg is None else '❌'})")

    print("\n✅ All ContinuousEvent serialization/parsing working correctly!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)