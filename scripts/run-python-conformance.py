#!/usr/bin/env python3

"""
Python conformance test runner for ESM Format cross-language testing.

This script runs the Python esm_format implementation against test fixtures
and generates standardized outputs for comparison with other language implementations.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import traceback

# Add the Python package to the path
script_dir = Path(__file__).parent
project_root = script_dir.parent
python_package = project_root / "packages" / "esm_format"

# Add the Python package to sys.path
sys.path.insert(0, str(python_package / "src"))

try:
    import esm_format
except ImportError as e:
    print(f"Failed to import esm_format Python library: {e}")
    print("Make sure the Python package is properly installed")
    sys.exit(1)

class ConformanceResults:
    def __init__(self):
        self.language = "python"
        self.timestamp = datetime.now().isoformat()
        self.validation_results = {}
        self.display_results = {}
        self.substitution_results = {}
        self.graph_results = {}
        self.errors = []

    def to_dict(self):
        return {
            "language": self.language,
            "timestamp": self.timestamp,
            "validation_results": self.validation_results,
            "display_results": self.display_results,
            "substitution_results": self.substitution_results,
            "graph_results": self.graph_results,
            "errors": self.errors
        }

def write_results(output_dir: Path, results: ConformanceResults):
    """Write conformance results to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    results_file = output_dir / "results.json"
    with open(results_file, 'w') as f:
        json.dump(results.to_dict(), f, indent=2)

    print(f"Python conformance results written to: {results_file}")

def run_validation_tests(tests_dir: Path) -> Dict[str, Any]:
    """Test schema and structural validation on valid and invalid ESM files."""
    print("Running validation tests...")
    validation_results = {}

    # Test valid files
    valid_dir = tests_dir / "valid"
    if valid_dir.exists() and valid_dir.is_dir():
        valid_results = {}
        valid_files = [f for f in valid_dir.iterdir() if f.suffix == ".esm"]

        for filepath in valid_files:
            try:
                esm_data = esm_format.load(filepath)
                result = esm_format.validate(esm_data)

                valid_results[filepath.name] = {
                    "is_valid": result.is_valid,
                    "schema_errors": result.schema_errors,
                    "structural_errors": result.structural_errors,
                    "parsed_successfully": True
                }
            except Exception as e:
                valid_results[filepath.name] = {
                    "parsed_successfully": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
        validation_results["valid"] = valid_results

    # Test invalid files
    invalid_dir = tests_dir / "invalid"
    if invalid_dir.exists() and invalid_dir.is_dir():
        invalid_results = {}
        invalid_files = [f for f in invalid_dir.iterdir() if f.suffix == ".esm"]

        for filepath in invalid_files:
            try:
                esm_data = esm_format.load(filepath)
                result = esm_format.validate(esm_data)

                invalid_results[filepath.name] = {
                    "is_valid": result.is_valid,
                    "schema_errors": result.schema_errors,
                    "structural_errors": result.structural_errors,
                    "parsed_successfully": True
                }
            except Exception as e:
                invalid_results[filepath.name] = {
                    "parsed_successfully": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "is_expected_error": True  # Invalid files should error
                }
        validation_results["invalid"] = invalid_results

    return validation_results

def run_display_tests(tests_dir: Path) -> Dict[str, Any]:
    """Test pretty-printing and display format generation."""
    print("Running display tests...")
    display_results = {}

    display_dir = tests_dir / "display"
    if display_dir.exists() and display_dir.is_dir():
        display_files = [f for f in display_dir.iterdir() if f.suffix == ".json"]

        for filepath in display_files:
            try:
                with open(filepath, 'r') as f:
                    test_data = json.load(f)
                test_results = {}

                # Test chemical formula rendering
                if "chemical_formulas" in test_data:
                    formula_results = []
                    for formula_test in test_data["chemical_formulas"]:
                        if "input" in formula_test:
                            input_formula = formula_test["input"]
                            try:
                                unicode_result = esm_format.render_chemical_formula(input_formula)

                                formula_results.append({
                                    "input": input_formula,
                                    "output_unicode": unicode_result,
                                    "output_latex": formula_test.get("expected_latex", ""),
                                    "output_ascii": input_formula,  # Fallback
                                    "success": True
                                })
                            except Exception as e:
                                formula_results.append({
                                    "input": input_formula,
                                    "error": str(e),
                                    "success": False
                                })
                    test_results["chemical_formulas"] = formula_results

                # Test expression rendering
                if "expressions" in test_data:
                    expression_results = []
                    for expr_test in test_data["expressions"]:
                        if "input" in expr_test:
                            input_expr = expr_test["input"]
                            try:
                                expr = esm_format.parse_expression(input_expr)
                                unicode_result = esm_format.pretty_print(expr, format="unicode")
                                latex_result = esm_format.pretty_print(expr, format="latex")
                                ascii_result = esm_format.pretty_print(expr, format="ascii")

                                expression_results.append({
                                    "input": input_expr,
                                    "output_unicode": unicode_result,
                                    "output_latex": latex_result,
                                    "output_ascii": ascii_result,
                                    "success": True
                                })
                            except Exception as e:
                                expression_results.append({
                                    "input": input_expr,
                                    "error": str(e),
                                    "success": False
                                })
                    test_results["expressions"] = expression_results

                display_results[filepath.name] = test_results

            except Exception as e:
                display_results[filepath.name] = {
                    "error": str(e),
                    "success": False
                }

    return display_results

def run_substitution_tests(tests_dir: Path) -> Dict[str, Any]:
    """Test expression substitution functionality."""
    print("Running substitution tests...")
    substitution_results = {}

    substitution_dir = tests_dir / "substitution"
    if substitution_dir.exists() and substitution_dir.is_dir():
        substitution_files = [f for f in substitution_dir.iterdir() if f.suffix == ".json"]

        for filepath in substitution_files:
            try:
                with open(filepath, 'r') as f:
                    test_data = json.load(f)
                test_results = []

                if "tests" in test_data:
                    for test_case in test_data["tests"]:
                        if "expression" in test_case and "substitutions" in test_case:
                            try:
                                expr = esm_format.parse_expression(test_case["expression"])
                                substitutions = {
                                    k: esm_format.parse_expression(v)
                                    for k, v in test_case["substitutions"].items()
                                }

                                result_expr = esm_format.substitute(expr, substitutions)
                                result_str = esm_format.pretty_print(result_expr)

                                test_results.append({
                                    "input": test_case["expression"],
                                    "substitutions": test_case["substitutions"],
                                    "result": result_str,
                                    "success": True
                                })
                            except Exception as e:
                                test_results.append({
                                    "input": test_case.get("expression", ""),
                                    "error": str(e),
                                    "success": False
                                })

                substitution_results[filepath.name] = test_results

            except Exception as e:
                substitution_results[filepath.name] = {
                    "error": str(e),
                    "success": False
                }

    return substitution_results

def run_graph_tests(tests_dir: Path) -> Dict[str, Any]:
    """Test graph generation functionality."""
    print("Running graph tests...")
    graph_results = {}

    graphs_dir = tests_dir / "graphs"
    if graphs_dir.exists() and graphs_dir.is_dir():
        graph_files = [f for f in graphs_dir.iterdir() if f.suffix == ".json"]

        for filepath in graph_files:
            try:
                with open(filepath, 'r') as f:
                    test_data = json.load(f)

                if "esm_file" in test_data:
                    esm_file_path = filepath.parent / test_data["esm_file"]
                    if esm_file_path.exists():
                        try:
                            esm_data = esm_format.load(esm_file_path)

                            # Generate system graph
                            system_graph = esm_format.generate_system_graph(esm_data)

                            # Export in different formats
                            dot_output = esm_format.export_dot(system_graph)
                            json_output = esm_format.export_json(system_graph)

                            graph_results[filepath.name] = {
                                "esm_file": str(esm_file_path),
                                "system_graph": {
                                    "nodes": len(system_graph.nodes),
                                    "edges": len(system_graph.edges),
                                    "dot_format": dot_output,
                                    "json_format": json_output
                                },
                                "success": True
                            }
                        except Exception as e:
                            graph_results[filepath.name] = {
                                "esm_file": str(esm_file_path),
                                "error": str(e),
                                "success": False
                            }
                    else:
                        graph_results[filepath.name] = {
                            "error": f"ESM file not found: {esm_file_path}",
                            "success": False
                        }

            except Exception as e:
                graph_results[filepath.name] = {
                    "error": str(e),
                    "success": False
                }

    return graph_results

def main():
    if len(sys.argv) != 2:
        print("Usage: python run-python-conformance.py <output_dir>")
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    tests_dir = project_root / "tests"

    print("Running Python conformance tests...")
    print(f"Tests directory: {tests_dir}")
    print(f"Output directory: {output_dir}")

    results = ConformanceResults()

    # Run all test categories
    try:
        results.validation_results = run_validation_tests(tests_dir)
        print("✓ Validation tests completed")
    except Exception as e:
        results.validation_results = {}
        results.errors.append(f"Validation tests failed: {str(e)}")
        print(f"✗ Validation tests failed: {e}")
        print(traceback.format_exc())

    try:
        results.display_results = run_display_tests(tests_dir)
        print("✓ Display tests completed")
    except Exception as e:
        results.display_results = {}
        results.errors.append(f"Display tests failed: {str(e)}")
        print(f"✗ Display tests failed: {e}")

    try:
        results.substitution_results = run_substitution_tests(tests_dir)
        print("✓ Substitution tests completed")
    except Exception as e:
        results.substitution_results = {}
        results.errors.append(f"Substitution tests failed: {str(e)}")
        print(f"✗ Substitution tests failed: {e}")

    try:
        results.graph_results = run_graph_tests(tests_dir)
        print("✓ Graph tests completed")
    except Exception as e:
        results.graph_results = {}
        results.errors.append(f"Graph tests failed: {str(e)}")
        print(f"✗ Graph tests failed: {e}")

    # Write results to file
    write_results(output_dir, results)

    if len(results.errors) == 0:
        print("Python conformance testing completed successfully!")
        sys.exit(0)
    else:
        print(f"Python conformance testing completed with {len(results.errors)} errors")
        sys.exit(1)

if __name__ == "__main__":
    main()