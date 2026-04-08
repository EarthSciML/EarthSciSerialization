#!/usr/bin/env python3
"""
ESM Format Compliance Matrix Verification Tool

This script verifies that the compliance matrix has:
1. Complete requirement coverage (no orphaned requirements)
2. Valid test fixture mappings
3. Consistent requirement IDs and categories
4. Proper cross-references

Usage:
    python verify_coverage.py
    python verify_coverage.py --check-fixtures  # Also check if test files exist
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple

def load_compliance_matrix() -> Dict:
    """Load the compliance matrix JSON file."""
    matrix_path = Path(__file__).parent / "compliance_matrix.json"
    if not matrix_path.exists():
        print(f"ERROR: Compliance matrix not found at {matrix_path}")
        sys.exit(1)

    with open(matrix_path) as f:
        return json.load(f)

def verify_requirement_ids(matrix: Dict) -> List[str]:
    """Verify requirement IDs follow the expected format and are consistent."""
    errors = []
    requirements = matrix.get("requirements", {})
    categories = matrix.get("requirement_categories", {})

    for req_id, req_data in requirements.items():
        # Check ID format: CATEGORY-SECTION-SUBSECTION-NUMBER or CATEGORY-SECTION-NUMBER
        parts = req_id.split("-")
        if len(parts) < 3 or len(parts) > 4:
            errors.append(f"Invalid requirement ID format: {req_id}")
            continue

        category = parts[0]

        # Check category exists
        if category not in categories:
            errors.append(f"Unknown category in requirement ID {req_id}: {category}")

        # Check requirement has category field matching ID
        if req_data.get("category") != category:
            errors.append(f"Requirement {req_id} category mismatch: ID says {category}, data says {req_data.get('category')}")

    return errors

def verify_test_fixture_mappings(matrix: Dict) -> List[str]:
    """Verify test fixture mappings are consistent and complete."""
    errors = []
    requirements = matrix.get("requirements", {})
    test_mappings = matrix.get("test_fixture_mapping", {})

    # Track which requirements have test coverage
    covered_requirements = set()

    for fixture_path, fixture_data in test_mappings.items():
        requirements_covered = fixture_data.get("requirements_covered", [])

        for req_id in requirements_covered:
            if req_id not in requirements:
                errors.append(f"Test fixture {fixture_path} references unknown requirement: {req_id}")
            else:
                covered_requirements.add(req_id)

    # Check for requirements without test coverage
    all_requirements = set(requirements.keys())
    uncovered = all_requirements - covered_requirements
    if uncovered:
        errors.append(f"Requirements without test coverage: {sorted(uncovered)}")

    # Verify requirements reference their test fixtures
    for req_id, req_data in requirements.items():
        test_fixtures = req_data.get("test_fixtures", [])

        for fixture_path in test_fixtures:
            if fixture_path not in test_mappings:
                errors.append(f"Requirement {req_id} references unmapped test fixture: {fixture_path}")

    return errors

def verify_coverage_statistics(matrix: Dict) -> List[str]:
    """Verify coverage statistics match actual data."""
    errors = []
    requirements = matrix.get("requirements", {})
    categories = matrix.get("requirement_categories", {})
    stats = matrix.get("coverage_statistics", {})

    # Check total count
    actual_total = len(requirements)
    expected_total = stats.get("total_requirements", 0)
    if actual_total != expected_total:
        errors.append(f"Total requirements mismatch: actual {actual_total}, reported {expected_total}")

    # Check category counts
    actual_by_category = {}
    for req_data in requirements.values():
        category = req_data.get("category", "UNKNOWN")
        actual_by_category[category] = actual_by_category.get(category, 0) + 1

    expected_by_category = stats.get("requirements_by_category", {})

    for category in categories.keys():
        actual_count = actual_by_category.get(category, 0)
        expected_count = expected_by_category.get(category, 0)
        if actual_count != expected_count:
            errors.append(f"Category {category} count mismatch: actual {actual_count}, reported {expected_count}")

    # Check priority counts
    actual_by_priority = {}
    for req_data in requirements.values():
        priority = req_data.get("priority", "UNKNOWN")
        actual_by_priority[priority] = actual_by_priority.get(priority, 0) + 1

    expected_by_priority = stats.get("requirements_by_priority", {})
    for priority in ["P1", "P2"]:
        actual_count = actual_by_priority.get(priority, 0)
        expected_count = expected_by_priority.get(priority, 0)
        if actual_count != expected_count:
            errors.append(f"Priority {priority} count mismatch: actual {actual_count}, reported {expected_count}")

    return errors

def check_test_fixture_files(matrix: Dict, base_path: Path) -> List[str]:
    """Check if test fixture files actually exist."""
    errors = []
    test_mappings = matrix.get("test_fixture_mapping", {})

    for fixture_path in test_mappings.keys():
        full_path = base_path / fixture_path
        if not full_path.exists():
            errors.append(f"Test fixture file does not exist: {fixture_path}")

    return errors

def verify_spec_references(matrix: Dict) -> List[str]:
    """Verify spec references are properly formatted."""
    errors = []
    requirements = matrix.get("requirements", {})

    valid_specs = ["esm-spec.md", "esm-libraries-spec.md"]

    for req_id, req_data in requirements.items():
        spec_ref = req_data.get("spec_ref", "")
        if not spec_ref:
            errors.append(f"Requirement {req_id} missing spec_ref")
            continue

        if ":" not in spec_ref:
            errors.append(f"Requirement {req_id} spec_ref missing section: {spec_ref}")
            continue

        spec_file, section = spec_ref.split(":", 1)
        if spec_file not in valid_specs:
            errors.append(f"Requirement {req_id} references unknown spec file: {spec_file}")

    return errors

def generate_coverage_report(matrix: Dict) -> str:
    """Generate a summary coverage report."""
    requirements = matrix.get("requirements", {})
    categories = matrix.get("requirement_categories", {})
    test_mappings = matrix.get("test_fixture_mapping", {})

    report = ["=== ESM Format Compliance Coverage Report ===\n"]

    # Overall statistics
    total_requirements = len(requirements)
    total_fixtures = len(test_mappings)

    report.append(f"Total Requirements: {total_requirements}")
    report.append(f"Total Test Fixtures: {total_fixtures}")

    # Coverage by category
    report.append("\n=== Coverage by Category ===")
    category_counts = {}
    for req_data in requirements.values():
        category = req_data.get("category", "UNKNOWN")
        category_counts[category] = category_counts.get(category, 0) + 1

    for category in sorted(category_counts.keys()):
        count = category_counts[category]
        category_info = categories.get(category, {})
        name = category_info.get("name", category)
        priority = category_info.get("priority", "Unknown")
        report.append(f"  {category}: {count} requirements ({name}, {priority})")

    # Priority distribution
    report.append("\n=== Priority Distribution ===")
    priority_counts = {}
    for req_data in requirements.values():
        priority = req_data.get("priority", "Unknown")
        priority_counts[priority] = priority_counts.get(priority, 0) + 1

    for priority in sorted(priority_counts.keys()):
        count = priority_counts[priority]
        percentage = (count / total_requirements) * 100
        report.append(f"  {priority}: {count} requirements ({percentage:.1f}%)")

    # Test fixture coverage
    covered_requirements = set()
    for fixture_data in test_mappings.values():
        covered_requirements.update(fixture_data.get("requirements_covered", []))

    coverage_percentage = (len(covered_requirements) / total_requirements) * 100
    report.append(f"\n=== Test Coverage ===")
    report.append(f"Requirements with test coverage: {len(covered_requirements)}/{total_requirements} ({coverage_percentage:.1f}%)")

    uncovered = set(requirements.keys()) - covered_requirements
    if uncovered:
        report.append(f"Uncovered requirements: {sorted(uncovered)}")
    else:
        report.append("✅ All requirements have test coverage")

    return "\n".join(report)

def main():
    parser = argparse.ArgumentParser(description="Verify ESM compliance matrix completeness and consistency")
    parser.add_argument("--check-fixtures", action="store_true",
                       help="Also check if test fixture files exist on disk")
    parser.add_argument("--report", action="store_true",
                       help="Generate coverage report")
    args = parser.parse_args()

    # Load the compliance matrix
    matrix = load_compliance_matrix()

    all_errors = []

    # Run all verification checks
    all_errors.extend(verify_requirement_ids(matrix))
    all_errors.extend(verify_test_fixture_mappings(matrix))
    all_errors.extend(verify_coverage_statistics(matrix))
    all_errors.extend(verify_spec_references(matrix))

    # Optionally check if test files exist
    if args.check_fixtures:
        base_path = Path(__file__).parent.parent.parent  # Go up to repo root
        all_errors.extend(check_test_fixture_files(matrix, base_path))

    # Generate report if requested
    if args.report:
        print(generate_coverage_report(matrix))
        print()

    # Report results
    if all_errors:
        print("❌ VERIFICATION FAILED")
        print(f"Found {len(all_errors)} errors:")
        for i, error in enumerate(all_errors, 1):
            print(f"  {i}. {error}")
        sys.exit(1)
    else:
        print("✅ VERIFICATION PASSED")
        print("Compliance matrix is complete and consistent")

        if not args.check_fixtures:
            print("\nNote: Run with --check-fixtures to verify test files exist on disk")

if __name__ == "__main__":
    main()