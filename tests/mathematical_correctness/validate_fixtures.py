#!/usr/bin/env python3
"""
Validation script for mathematical correctness test fixtures.

This script validates that all test fixtures are properly formatted,
contain required fields, and have reasonable values for all parameters.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Union

def validate_json_file(filepath: Path) -> tuple[bool, List[str]]:
    """Validate a JSON file and return success status and error messages."""
    errors = []

    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"JSON parsing error: {e}"]
    except FileNotFoundError:
        return False, [f"File not found: {filepath}"]
    except Exception as e:
        return False, [f"Unexpected error reading file: {e}"]

    # Validate meta section
    if 'meta' not in data:
        errors.append("Missing 'meta' section")
    else:
        meta = data['meta']
        required_meta_fields = ['name', 'version', 'description', 'mathematical_type', 'test_cases']
        for field in required_meta_fields:
            if field not in meta:
                errors.append(f"Missing required meta field: {field}")

    return len(errors) == 0, errors

def validate_conservation_laws(data: Dict[str, Any]) -> List[str]:
    """Validate conservation laws test fixture."""
    errors = []

    if 'reaction_systems' not in data:
        errors.append("Missing 'reaction_systems' section")
        return errors

    reaction_systems = data['reaction_systems']
    if not isinstance(reaction_systems, list):
        errors.append("'reaction_systems' must be a list")
        return errors

    for i, system in enumerate(reaction_systems):
        system_errors = []

        # Check required fields
        required_fields = ['name', 'description', 'species', 'reactions']
        for field in required_fields:
            if field not in system:
                system_errors.append(f"Missing required field: {field}")

        # Validate species
        if 'species' in system and isinstance(system['species'], list):
            for j, species in enumerate(system['species']):
                if 'name' not in species:
                    system_errors.append(f"Species {j} missing 'name' field")
                if 'mass' in species and not isinstance(species['mass'], (int, float)):
                    system_errors.append(f"Species {j} 'mass' must be numeric")

        # Validate reactions
        if 'reactions' in system and isinstance(system['reactions'], list):
            for j, reaction in enumerate(system['reactions']):
                if 'name' not in reaction:
                    system_errors.append(f"Reaction {j} missing 'name' field")
                if 'reactants' not in reaction:
                    system_errors.append(f"Reaction {j} missing 'reactants' field")
                if 'products' not in reaction:
                    system_errors.append(f"Reaction {j} missing 'products' field")

        # Validate test criteria
        if 'test_criteria' in system:
            criteria = system['test_criteria']
            if 'mass_balance_tolerance' in criteria:
                tol = criteria['mass_balance_tolerance']
                if not isinstance(tol, (int, float)) or tol <= 0:
                    system_errors.append("Invalid mass_balance_tolerance")

        if system_errors:
            errors.append(f"Reaction system {i} ({system.get('name', 'unnamed')}): {'; '.join(system_errors)}")

    return errors

def validate_dimensional_analysis(data: Dict[str, Any]) -> List[str]:
    """Validate dimensional analysis test fixture."""
    errors = []

    if 'dimensional_equations' not in data:
        errors.append("Missing 'dimensional_equations' section")
        return errors

    equations = data['dimensional_equations']
    if not isinstance(equations, list):
        errors.append("'dimensional_equations' must be a list")
        return errors

    for i, equation in enumerate(equations):
        equation_errors = []

        # Check required fields
        required_fields = ['name', 'equation', 'variables', 'dimensional_consistency']
        for field in required_fields:
            if field not in equation:
                equation_errors.append(f"Missing required field: {field}")

        # Validate variables
        if 'variables' in equation and isinstance(equation['variables'], dict):
            for var_name, var_info in equation['variables'].items():
                if not isinstance(var_info, dict):
                    equation_errors.append(f"Variable {var_name} info must be a dict")
                elif 'dimension' not in var_info:
                    equation_errors.append(f"Variable {var_name} missing 'dimension' field")

        # Validate dimensional consistency
        if 'dimensional_consistency' in equation:
            if not isinstance(equation['dimensional_consistency'], bool):
                equation_errors.append("'dimensional_consistency' must be boolean")

        # Validate tolerance if present
        if 'tolerance' in equation:
            tol = equation['tolerance']
            if not isinstance(tol, (int, float)) or tol <= 0:
                equation_errors.append("Invalid tolerance value")

        if equation_errors:
            errors.append(f"Equation {i} ({equation.get('name', 'unnamed')}): {'; '.join(equation_errors)}")

    return errors

def validate_numerical_correctness(data: Dict[str, Any]) -> List[str]:
    """Validate numerical correctness test fixture."""
    errors = []

    if 'floating_point_precision_tests' not in data:
        errors.append("Missing 'floating_point_precision_tests' section")
        return errors

    precision_tests = data['floating_point_precision_tests']
    if not isinstance(precision_tests, list):
        errors.append("'floating_point_precision_tests' must be a list")
        return errors

    for i, test in enumerate(precision_tests):
        test_errors = []

        # Check required fields
        required_fields = ['name', 'description']
        for field in required_fields:
            if field not in test:
                test_errors.append(f"Missing required field: {field}")

        # Validate test-specific fields based on test name
        if 'name' in test:
            test_name = test['name']

            if test_name == 'machine_epsilon_verification':
                if 'test_values' not in test:
                    test_errors.append("Missing 'test_values' field")
                elif not isinstance(test['test_values'], dict):
                    test_errors.append("'test_values' must be a dict")

            elif test_name == 'catastrophic_cancellation':
                if 'test_cases' not in test:
                    test_errors.append("Missing 'test_cases' field")
                elif not isinstance(test['test_cases'], list):
                    test_errors.append("'test_cases' must be a list")

        if test_errors:
            errors.append(f"Precision test {i} ({test.get('name', 'unnamed')}): {'; '.join(test_errors)}")

    return errors

def validate_algebraic_verification(data: Dict[str, Any]) -> List[str]:
    """Validate algebraic verification test fixture."""
    errors = []

    if 'expression_simplification_tests' not in data:
        errors.append("Missing 'expression_simplification_tests' section")
        return errors

    simplification_tests = data['expression_simplification_tests']
    if not isinstance(simplification_tests, list):
        errors.append("'expression_simplification_tests' must be a list")
        return errors

    for i, test in enumerate(simplification_tests):
        test_errors = []

        # Check required fields
        required_fields = ['name', 'test_cases']
        for field in required_fields:
            if field not in test:
                test_errors.append(f"Missing required field: {field}")

        # Validate test cases
        if 'test_cases' in test and isinstance(test['test_cases'], list):
            for j, case in enumerate(test['test_cases']):
                if 'expression' not in case:
                    test_errors.append(f"Test case {j} missing 'expression' field")
                if 'simplified' not in case:
                    test_errors.append(f"Test case {j} missing 'simplified' field")
                if 'verification_points' in case and not isinstance(case['verification_points'], list):
                    test_errors.append(f"Test case {j} 'verification_points' must be a list")

        if test_errors:
            errors.append(f"Simplification test {i} ({test.get('name', 'unnamed')}): {'; '.join(test_errors)}")

    return errors

def validate_performance_benchmarks(data: Dict[str, Any]) -> List[str]:
    """Validate performance benchmarks test fixture."""
    errors = []

    if 'benchmark_categories' not in data:
        errors.append("Missing 'benchmark_categories' section")
        return errors

    categories = data['benchmark_categories']
    if not isinstance(categories, list):
        errors.append("'benchmark_categories' must be a list")
        return errors

    for i, category in enumerate(categories):
        category_errors = []

        # Check required fields
        required_fields = ['name', 'description', 'complexity', 'benchmarks']
        for field in required_fields:
            if field not in category:
                category_errors.append(f"Missing required field: {field}")

        # Validate benchmarks
        if 'benchmarks' in category and isinstance(category['benchmarks'], list):
            for j, benchmark in enumerate(category['benchmarks']):
                if 'name' not in benchmark:
                    category_errors.append(f"Benchmark {j} missing 'name' field")
                if 'target_performance' in benchmark:
                    target = benchmark['target_performance']
                    if not isinstance(target, dict):
                        category_errors.append(f"Benchmark {j} 'target_performance' must be a dict")

        if category_errors:
            errors.append(f"Benchmark category {i} ({category.get('name', 'unnamed')}): {'; '.join(category_errors)}")

    return errors

def main():
    """Main validation function."""
    script_dir = Path(__file__).parent
    fixture_files = {
        'conservation_laws.esm': validate_conservation_laws,
        'dimensional_analysis.esm': validate_dimensional_analysis,
        'numerical_correctness.esm': validate_numerical_correctness,
        'algebraic_verification.esm': validate_algebraic_verification,
        'performance_benchmarks.esm': validate_performance_benchmarks
    }

    all_valid = True
    total_errors = 0

    print("Mathematical Correctness Test Fixtures Validation")
    print("=" * 50)

    for filename, validator in fixture_files.items():
        filepath = script_dir / filename
        print(f"\nValidating {filename}...")

        # Basic JSON validation
        is_valid_json, json_errors = validate_json_file(filepath)
        if not is_valid_json:
            print(f"  ❌ JSON validation failed:")
            for error in json_errors:
                print(f"    - {error}")
            all_valid = False
            total_errors += len(json_errors)
            continue

        # Content validation
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            content_errors = validator(data)
            if content_errors:
                print(f"  ❌ Content validation failed:")
                for error in content_errors:
                    print(f"    - {error}")
                all_valid = False
                total_errors += len(content_errors)
            else:
                print(f"  ✅ Validation passed")

        except Exception as e:
            print(f"  ❌ Validation error: {e}")
            all_valid = False
            total_errors += 1

    # Summary
    print("\n" + "=" * 50)
    if all_valid:
        print("🎉 All test fixtures are valid!")
        return 0
    else:
        print(f"❌ Validation failed with {total_errors} errors")
        return 1

if __name__ == "__main__":
    sys.exit(main())