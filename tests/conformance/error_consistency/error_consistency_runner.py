#!/usr/bin/env python3
"""
Cross-language error consistency test runner.

This script runs the same invalid ESM files across all language implementations
(Julia, TypeScript, Python) and compares their validation error outputs to ensure
consistent error codes across implementations.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse


class ErrorConsistencyRunner:
    """Runs validation tests across all language implementations."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.invalid_tests_dir = project_root / "tests" / "invalid"
        self.results_dir = project_root / "tests" / "conformance" / "results" / "error_consistency"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def get_invalid_test_files(self) -> List[Path]:
        """Get all .esm files from the invalid tests directory."""
        return list(self.invalid_tests_dir.glob("*.esm"))

    def validate_with_julia(self, esm_file: Path) -> Dict[str, Any]:
        """Run validation using the Julia implementation."""
        julia_dir = self.project_root / "packages" / "ESMFormat.jl"

        # Create a temporary Julia script to run validation
        julia_script = f'''
        using Pkg
        Pkg.activate("{julia_dir}")
        using ESMFormat
        using JSON3

        try
            result = ESMFormat.load("{esm_file}")
            validation = ESMFormat.validate(result)

            # Convert to standardized format
            output = Dict(
                "language" => "julia",
                "file" => "{esm_file.name}",
                "validation_result" => Dict(
                    "valid" => validation.is_valid,
                    "schema_errors" => [
                        Dict(
                            "path" => err.path,
                            "message" => err.message,
                            "keyword" => get(err, :keyword, "")
                        ) for err in validation.schema_errors
                    ],
                    "structural_errors" => [
                        Dict(
                            "path" => err.path,
                            "code" => err.code,
                            "message" => err.message,
                            "details" => err.details
                        ) for err in validation.structural_errors
                    ]
                )
            )

            println(JSON3.write(output))
        catch e
            # Handle load errors (malformed JSON, schema violations)
            error_output = Dict(
                "language" => "julia",
                "file" => "{esm_file.name}",
                "load_error" => Dict(
                    "type" => string(typeof(e)),
                    "message" => string(e)
                )
            )
            println(JSON3.write(error_output))
        end
        '''

        try:
            result = subprocess.run(
                ["julia", "--project=" + str(julia_dir), "-e", julia_script],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout.strip())
            else:
                return {
                    "language": "julia",
                    "file": esm_file.name,
                    "error": {
                        "type": "execution_error",
                        "returncode": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    }
                }
        except subprocess.TimeoutExpired:
            return {
                "language": "julia",
                "file": esm_file.name,
                "error": {"type": "timeout", "message": "Julia validation timed out"}
            }
        except Exception as e:
            return {
                "language": "julia",
                "file": esm_file.name,
                "error": {"type": "exception", "message": str(e)}
            }

    def validate_with_typescript(self, esm_file: Path) -> Dict[str, Any]:
        """Run validation using the TypeScript implementation."""
        ts_dir = self.project_root / "packages" / "esm-format"

        # Create a temporary TypeScript script that uses the validate function
        ts_script = f'''
        import {{ readFileSync }} from 'fs';
        import {{ validate }} from '{ts_dir}/dist/esm/index.js';

        try {{
            const content = readFileSync("{esm_file}", "utf8");

            // Use the full validate function which includes both schema and structural validation
            const validationResult = validate(content);

            const output = {{
                language: "typescript",
                file: "{esm_file.name}",
                validation_result: {{
                    valid: validationResult.is_valid,
                    schema_errors: validationResult.schema_errors,
                    structural_errors: validationResult.structural_errors
                }}
            }};

            console.log(JSON.stringify(output));
        }} catch (e) {{
            const errorOutput = {{
                language: "typescript",
                file: "{esm_file.name}",
                load_error: {{
                    type: e.constructor.name,
                    message: e.message
                }}
            }};
            console.log(JSON.stringify(errorOutput));
        }}
        '''

        try:
            # Write the script to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mjs', delete=False) as f:
                f.write(ts_script)
                temp_script = f.name

            result = subprocess.run(
                ["node", temp_script],
                cwd=ts_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Clean up temp file
            os.unlink(temp_script)

            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout.strip())
            else:
                return {
                    "language": "typescript",
                    "file": esm_file.name,
                    "error": {
                        "type": "execution_error",
                        "returncode": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    }
                }
        except subprocess.TimeoutExpired:
            return {
                "language": "typescript",
                "file": esm_file.name,
                "error": {"type": "timeout", "message": "TypeScript validation timed out"}
            }
        except Exception as e:
            return {
                "language": "typescript",
                "file": esm_file.name,
                "error": {"type": "exception", "message": str(e)}
            }

    def validate_with_python(self, esm_file: Path) -> Dict[str, Any]:
        """Run validation using the Python implementation."""
        python_dir = self.project_root / "packages" / "esm_format"
        venv_python = python_dir / "venv" / "bin" / "python"

        python_script = f'''
import sys
sys.path.insert(0, "{python_dir / 'src'}")

import json
from esm_format import validate

try:
    with open("{esm_file}", "r") as f:
        content = f.read()

    # Validate with raw data (string or dict)
    validation = validate(content)

    # Convert validation errors to dictionaries for JSON serialization
    schema_errors = []
    for error in validation.schema_errors:
        schema_errors.append({{
            "path": error.path,
            "message": error.message,
            "code": error.code,
            "details": error.details
        }})

    structural_errors = []
    for error in validation.structural_errors:
        structural_errors.append({{
            "path": error.path,
            "message": error.message,
            "code": error.code,
            "details": error.details
        }})

    output = {{
        "language": "python",
        "file": "{esm_file.name}",
        "validation_result": {{
            "valid": validation.is_valid,
            "schema_errors": schema_errors,
            "structural_errors": structural_errors
        }}
    }}

    print(json.dumps(output))
except Exception as e:
    error_output = {{
        "language": "python",
        "file": "{esm_file.name}",
        "load_error": {{
            "type": type(e).__name__,
            "message": str(e)
        }}
    }}
    print(json.dumps(error_output))
'''

        try:
            result = subprocess.run(
                [str(venv_python), "-c", python_script],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout.strip())
            else:
                return {
                    "language": "python",
                    "file": esm_file.name,
                    "error": {
                        "type": "execution_error",
                        "returncode": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    }
                }
        except subprocess.TimeoutExpired:
            return {
                "language": "python",
                "file": esm_file.name,
                "error": {"type": "timeout", "message": "Python validation timed out"}
            }
        except Exception as e:
            return {
                "language": "python",
                "file": esm_file.name,
                "error": {"type": "exception", "message": str(e)}
            }

    def run_single_file_test(self, esm_file: Path) -> Dict[str, Any]:
        """Run validation test for a single ESM file across all languages."""
        print(f"Testing {esm_file.name}...")

        results = {
            "file": esm_file.name,
            "julia": self.validate_with_julia(esm_file),
            "typescript": self.validate_with_typescript(esm_file),
            "python": self.validate_with_python(esm_file)
        }

        return results

    def run_all_tests(self, test_files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run validation tests for all invalid ESM files."""
        invalid_files = self.get_invalid_test_files()

        if test_files:
            # Filter to only specified test files
            invalid_files = [f for f in invalid_files if f.name in test_files]

        all_results = {}

        for esm_file in invalid_files:
            try:
                result = self.run_single_file_test(esm_file)
                all_results[esm_file.name] = result
            except Exception as e:
                print(f"Error testing {esm_file.name}: {e}")
                all_results[esm_file.name] = {
                    "file": esm_file.name,
                    "error": str(e)
                }

        return all_results

    def save_results(self, results: Dict[str, Any], output_file: str = "cross_language_validation_results.json"):
        """Save test results to a JSON file."""
        output_path = self.results_dir / output_file
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"Results saved to {output_path}")
        return output_path


def main():
    parser = argparse.ArgumentParser(description="Run cross-language ESM validation error consistency tests")
    parser.add_argument("--files", nargs="*", help="Specific test files to run (default: all)")
    parser.add_argument("--output", default="cross_language_validation_results.json",
                       help="Output filename for results")

    args = parser.parse_args()

    # Find project root (look for esm-schema.json)
    current_dir = Path(__file__).parent
    project_root = current_dir
    while project_root != project_root.parent:
        if (project_root / "esm-schema.json").exists():
            break
        project_root = project_root.parent
    else:
        print("Error: Could not find project root (esm-schema.json not found)")
        sys.exit(1)

    runner = ErrorConsistencyRunner(project_root)

    print(f"Running error consistency tests...")
    print(f"Project root: {project_root}")
    print(f"Invalid tests directory: {runner.invalid_tests_dir}")
    print(f"Results directory: {runner.results_dir}")

    results = runner.run_all_tests(args.files)
    output_path = runner.save_results(results, args.output)

    print(f"\\nTested {len(results)} files.")
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()