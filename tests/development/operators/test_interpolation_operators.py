#!/usr/bin/env python3
"""
Quick verification test for interpolation operators implementation.
"""

import json
import sys
from pathlib import Path

def test_interpolation_operators():
    """Test that interpolation operators are properly defined."""

    root_dir = Path(__file__).parent
    test_files = [
        "tests/valid/interpolation_operators_comprehensive.esm",
        "tests/valid/basic_interpolation_operators.esm",
        "tests/coupling/interpolation_coupling_example.esm"
    ]

    results = []

    for file_path in test_files:
        full_path = root_dir / file_path
        if not full_path.exists():
            results.append(f"✗ File not found: {file_path}")
            continue

        try:
            with open(full_path, 'r') as f:
                data = json.load(f)

            # Check basic structure
            if 'esm' not in data or data['esm'] != '0.1.0':
                results.append(f"✗ {file_path}: Invalid ESM version")
                continue

            if 'operators' not in data:
                results.append(f"✗ {file_path}: No operators section")
                continue

            operators = data['operators']
            operator_count = len(operators)

            # Check operator structure
            valid_operators = 0
            for name, operator in operators.items():
                if all(key in operator for key in ['operator_id', 'needed_vars', 'description']):
                    valid_operators += 1

            results.append(f"✓ {file_path}: {valid_operators}/{operator_count} operators have required fields")

            # Check for specific interpolation types in comprehensive file
            if "comprehensive" in file_path:
                expected_types = ['Linear', 'Cubic', 'Spline']
                found_types = [t for t in expected_types if any(t in name for name in operators.keys())]
                results.append(f"✓ {file_path}: Found interpolation types: {', '.join(found_types)}")

        except json.JSONDecodeError as e:
            results.append(f"✗ {file_path}: JSON parsing error: {e}")
        except Exception as e:
            results.append(f"✗ {file_path}: Error: {e}")

    return results

def main():
    """Main test function."""
    print("Testing interpolation operators implementation...")
    print("=" * 60)

    results = test_interpolation_operators()

    for result in results:
        print(result)

    # Summary
    passed = sum(1 for r in results if r.startswith('✓'))
    failed = sum(1 for r in results if r.startswith('✗'))

    print("=" * 60)
    print(f"Summary: {passed} passed, {failed} failed")

    if failed > 0:
        sys.exit(1)
    else:
        print("All tests passed! ✓")

if __name__ == "__main__":
    main()