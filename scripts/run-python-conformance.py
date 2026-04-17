#!/usr/bin/env python3

"""
Python conformance test runner for ESM Format cross-language testing.

This script runs the Python earthsci_toolkit implementation against test fixtures
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
python_package = project_root / "packages" / "earthsci_toolkit"

# Add the Python package to sys.path
sys.path.insert(0, str(python_package / "src"))

try:
    import earthsci_toolkit
except ImportError as e:
    print(f"Failed to import earthsci_toolkit Python library: {e}")
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
        self.arrayop_results = {}
        self.errors = []

    def to_dict(self):
        return {
            "language": self.language,
            "timestamp": self.timestamp,
            "validation_results": self.validation_results,
            "display_results": self.display_results,
            "substitution_results": self.substitution_results,
            "graph_results": self.graph_results,
            "arrayop_results": self.arrayop_results,
            "errors": self.errors
        }

def write_results(output_dir: Path, results: ConformanceResults):
    """Write conformance results to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    results_file = output_dir / "results.json"
    with open(results_file, 'w') as f:
        json.dump(results.to_dict(), f, indent=2, default=str)

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
                esm_data = earthsci_toolkit.load(filepath)
                result = earthsci_toolkit.validate(esm_data)

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
                esm_data = earthsci_toolkit.load(filepath)
                result = earthsci_toolkit.validate(esm_data)

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
                                unicode_result = earthsci_toolkit.render_chemical_formula(input_formula)

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
                                expr = earthsci_toolkit.parse_expression(input_expr)
                                unicode_result = earthsci_toolkit.pretty_print(expr, format="unicode")
                                latex_result = earthsci_toolkit.pretty_print(expr, format="latex")
                                ascii_result = earthsci_toolkit.pretty_print(expr, format="ascii")

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
                                expr = earthsci_toolkit.parse_expression(test_case["expression"])
                                substitutions = {
                                    k: earthsci_toolkit.parse_expression(v)
                                    for k, v in test_case["substitutions"].items()
                                }

                                result_expr = earthsci_toolkit.substitute(expr, substitutions)
                                result_str = earthsci_toolkit.pretty_print(result_expr)

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
                            esm_data = earthsci_toolkit.load(esm_file_path)

                            # Generate system graph
                            system_graph = earthsci_toolkit.generate_system_graph(esm_data)

                            # Export in different formats
                            dot_output = earthsci_toolkit.export_dot(system_graph)
                            json_output = earthsci_toolkit.export_json(system_graph)

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

def _merge_tolerance(*tolerances) -> Dict[str, float]:
    merged: Dict[str, float] = {}
    for t in tolerances:
        if t:
            merged.update(t)
    return {
        "rel": float(merged.get("rel", 0.0)),
        "abs": float(merged.get("abs", 0.0)),
    }


def _lookup_actual(vars_list, y, t_arr, var_key, time) -> float:
    import numpy as np
    match_idx = None
    for i, name in enumerate(vars_list):
        if name == var_key or name.endswith("." + var_key):
            match_idx = i
            break
    if match_idx is None:
        raise KeyError(f"variable {var_key!r} not in result vars: {vars_list}")
    row = y[match_idx, :]
    if len(t_arr) == 0:
        raise ValueError("result has no time points")
    if time <= t_arr[0]:
        return float(row[0])
    if time >= t_arr[-1]:
        return float(row[-1])
    return float(np.interp(time, t_arr, row))


def _assertion_passes(actual, expected, rel, ab) -> bool:
    diff = abs(actual - expected)
    if ab > 0 and diff <= ab:
        return True
    if rel > 0:
        denom = max(abs(expected), 1e-12)
        if diff / denom <= rel:
            return True
    if ab == 0 and rel == 0:
        return diff == 0.0
    return False


def run_arrayop_tests(project_root: Path) -> Dict[str, Any]:
    """Run every inline test in every arrayop fixture, emit per-fixture results.

    Schema: {fixture: {model: {test_id: {success, message, assertions: [...]}}}}
    Each assertion records {variable, time, expected, actual, tolerance, passed}
    — ``actual`` is the scalar the binding produced, used for cross-language
    agreement diffing downstream.
    """
    print("Running arrayop simulation tests...")
    from earthsci_toolkit.simulation import simulate

    fixtures_dir = project_root / "tests" / "fixtures" / "arrayop"
    results: Dict[str, Any] = {}
    if not fixtures_dir.is_dir():
        return results

    for fixture_path in sorted(fixtures_dir.glob("*.esm")):
        fixture_key = fixture_path.name
        with open(fixture_path, "r") as fh:
            raw = json.load(fh)
        try:
            esm_file = earthsci_toolkit.load(fixture_path)
        except Exception as e:
            results[fixture_key] = {"__fixture_error": str(e)}
            continue

        fixture_out: Dict[str, Any] = {}
        for model_name, model_raw in (raw.get("models") or {}).items():
            tests = model_raw.get("tests") or []
            if not tests:
                continue
            model_tol = model_raw.get("tolerance") or {}
            model_out: Dict[str, Any] = {}
            for test in tests:
                test_id = test.get("id", "unknown")
                test_tol = test.get("tolerance") or {}
                tspan_raw = test.get("time_span") or {}
                tspan = (float(tspan_raw.get("start", 0.0)), float(tspan_raw.get("end", 0.0)))
                ics = {k: float(v) for k, v in (test.get("initial_conditions") or {}).items()}
                params = {k: float(v) for k, v in (test.get("parameter_overrides") or {}).items()}

                sim_ok = True
                sim_msg = ""
                sim_result = None
                try:
                    sim_result = simulate(
                        esm_file, tspan=tspan, initial_conditions=ics, parameters=params
                    )
                    if not getattr(sim_result, "success", True):
                        sim_ok = False
                        sim_msg = getattr(sim_result, "message", "") or ""
                except Exception as e:
                    sim_ok = False
                    sim_msg = f"{type(e).__name__}: {e}"

                assertions_out = []
                for assertion in test.get("assertions", []):
                    var_key = assertion["variable"]
                    time = float(assertion["time"])
                    expected = float(assertion["expected"])
                    merged = _merge_tolerance(
                        model_tol, test_tol, assertion.get("tolerance") or {}
                    )
                    rec: Dict[str, Any] = {
                        "variable": var_key,
                        "time": time,
                        "expected": expected,
                        "tolerance": merged,
                    }
                    if sim_ok and sim_result is not None:
                        try:
                            actual = _lookup_actual(
                                sim_result.vars, sim_result.y, sim_result.t,
                                var_key, time,
                            )
                            rec["actual"] = actual
                            rec["passed"] = _assertion_passes(
                                actual, expected, merged["rel"], merged["abs"]
                            )
                        except Exception as e:
                            rec["actual"] = None
                            rec["passed"] = False
                            rec["error"] = f"{type(e).__name__}: {e}"
                    else:
                        rec["actual"] = None
                        rec["passed"] = False
                    assertions_out.append(rec)

                model_out[test_id] = {
                    "success": sim_ok,
                    "message": sim_msg,
                    "assertions": assertions_out,
                }
            if model_out:
                fixture_out[model_name] = model_out
        results[fixture_key] = fixture_out

    return results


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

    try:
        results.arrayop_results = run_arrayop_tests(project_root)
        print("✓ Arrayop simulation tests completed")
    except Exception as e:
        results.arrayop_results = {}
        results.errors.append(f"Arrayop tests failed: {str(e)}")
        print(f"✗ Arrayop tests failed: {e}")
        print(traceback.format_exc())

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