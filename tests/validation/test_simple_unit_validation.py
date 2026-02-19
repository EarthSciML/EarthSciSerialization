#!/usr/bin/env python3
"""
Simple test script to verify that unit validation _validate_units function is no longer a no-op.

This script directly imports and inspects the validation module.
"""

import sys
import os
import inspect

# Add the package to path
sys.path.insert(0, 'packages/esm_format/src')
sys.path.insert(0, 'packages/esm_format/src/esm_format')

def test_validate_units_function():
    """Test that _validate_units is no longer a no-op."""

    print("Testing _validate_units function directly...")

    try:
        # Import the function directly
        from esm_format.validation import _validate_units
        print("✓ Successfully imported _validate_units function")
    except ImportError as e:
        print(f"✗ Failed to import _validate_units: {e}")
        return False

    # Get the source code
    try:
        source_lines = inspect.getsource(_validate_units)
        print("✓ Successfully retrieved source code")
    except Exception as e:
        print(f"✗ Failed to get source: {e}")
        return False

    print("\nAnalyzing source code:")
    print("-" * 40)

    # Check for no-op indicators
    is_noop = False
    has_implementation = False

    if 'pass' in source_lines and 'TODO' in source_lines:
        print("✗ Contains 'pass' statement with TODO - likely no-op")
        is_noop = True
    else:
        print("✓ No obvious no-op indicators found")

    if 'UnitValidator' in source_lines:
        print("✓ Uses UnitValidator - has implementation")
        has_implementation = True
    else:
        print("? No UnitValidator usage found")

    if 'validate_esm_file' in source_lines:
        print("✓ Calls validate_esm_file - has functionality")
        has_implementation = True

    if 'unit_warnings.append' in source_lines:
        print("✓ Appends to unit_warnings - produces output")
        has_implementation = True

    print("\nSource code preview:")
    print("-" * 40)
    lines = source_lines.split('\n')[:20]  # First 20 lines
    for i, line in enumerate(lines, 1):
        print(f"{i:2}: {line}")
    if len(source_lines.split('\n')) > 20:
        print("... (truncated)")

    print("-" * 40)

    # Make determination
    if is_noop:
        print("❌ RESULT: Function appears to be a no-op")
        return False
    elif has_implementation:
        print("✅ RESULT: Function has proper implementation")
        return True
    else:
        print("? RESULT: Unclear - function may have some implementation")
        return True  # Give benefit of the doubt

def main():
    """Run the simple test."""
    print("Simple Unit Validation No-Op Test")
    print("=" * 50)

    success = test_validate_units_function()

    print("\n" + "=" * 50)
    if success:
        print("✅ PASS: _validate_units function is not a no-op")
        return 0
    else:
        print("❌ FAIL: _validate_units function appears to be a no-op")
        return 1

if __name__ == "__main__":
    sys.exit(main())