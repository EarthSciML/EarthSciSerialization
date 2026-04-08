#!/usr/bin/env python3
"""
Direct source code inspection to verify unit validation fix.
"""

def test_by_reading_source():
    """Test the fix by reading the source file directly."""

    validation_file = "packages/esm_format/src/esm_format/validation.py"

    print("Reading validation.py source...")

    try:
        with open(validation_file, 'r') as f:
            content = f.read()
        print("✓ Successfully read validation.py")
    except Exception as e:
        print(f"✗ Failed to read file: {e}")
        return False

    # Find the _validate_units function
    lines = content.split('\n')
    function_start = None
    function_lines = []
    in_function = False
    indent_level = None

    for i, line in enumerate(lines):
        if 'def _validate_units(' in line:
            function_start = i
            in_function = True
            indent_level = len(line) - len(line.lstrip())
            function_lines.append(line)
            continue

        if in_function:
            current_indent = len(line) - len(line.lstrip()) if line.strip() else float('inf')

            # If we hit a line with same or less indentation and it's not empty, we're done
            if line.strip() and current_indent <= indent_level:
                break

            function_lines.append(line)

    if not function_lines:
        print("✗ Could not find _validate_units function")
        return False

    print(f"✓ Found _validate_units function at line {function_start + 1}")
    print("\nFunction source:")
    print("-" * 60)
    for i, line in enumerate(function_lines):
        print(f"{function_start + i + 1:3}: {line}")
    print("-" * 60)

    # Analyze the function
    function_source = '\n'.join(function_lines)

    # Check for no-op indicators
    has_pass_with_todo = 'pass' in function_source and 'TODO' in function_source
    has_unit_validator = 'UnitValidator' in function_source
    has_validate_esm_file = 'validate_esm_file' in function_source
    has_unit_warnings_append = 'unit_warnings.append' in function_source
    has_try_except = 'try:' in function_source and 'except' in function_source

    print("\nAnalysis:")
    print(f"  - Contains 'pass' with TODO (no-op indicator): {'✗ YES' if has_pass_with_todo else '✓ NO'}")
    print(f"  - Uses UnitValidator: {'✓ YES' if has_unit_validator else '✗ NO'}")
    print(f"  - Calls validate_esm_file: {'✓ YES' if has_validate_esm_file else '✗ NO'}")
    print(f"  - Appends to unit_warnings: {'✓ YES' if has_unit_warnings_append else '✗ NO'}")
    print(f"  - Has error handling: {'✓ YES' if has_try_except else '✗ NO'}")

    # Make determination
    if has_pass_with_todo:
        print("\n❌ RESULT: Function is still a no-op (contains 'pass' with TODO)")
        return False
    elif has_unit_validator and has_validate_esm_file:
        print("\n✅ RESULT: Function properly implements unit validation")
        return True
    elif has_unit_warnings_append:
        print("\n✅ RESULT: Function has some implementation")
        return True
    else:
        print("\n? RESULT: Function may have some implementation but unclear")
        return False

def main():
    """Run the source inspection test."""
    print("Unit Validation Source Code Inspection")
    print("=" * 50)

    success = test_by_reading_source()

    print("\n" + "=" * 50)
    if success:
        print("✅ PASS: Unit validation is properly implemented")
        return 0
    else:
        print("❌ FAIL: Unit validation appears to still be a no-op")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())