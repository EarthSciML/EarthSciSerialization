#!/usr/bin/env python3
"""
Simple test runner for error consistency validation.

Tests a small subset of invalid files to verify the cross-language
validation infrastructure is working correctly.
"""

import sys
from pathlib import Path
import subprocess


def main():
    # Get the current directory and project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent

    print("=== ESM Format Error Consistency Test ===")
    print(f"Project root: {project_root}")

    # Test files to check (subset for quick testing)
    test_files = [
        "complete_error_coverage.esm",
        "undefined_variable.esm",
        "equation_count_mismatch.esm"
    ]

    print(f"Testing {len(test_files)} files: {', '.join(test_files)}")

    try:
        # Run the error consistency runner
        runner_script = script_dir / "error_consistency_runner.py"
        cmd = [sys.executable, str(runner_script), "--files"] + test_files + ["--output", "test_results.json"]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=script_dir, check=True)

        if result.returncode == 0:
            print("✓ Error consistency runner completed successfully")

            # Run the comparison analysis
            compare_script = script_dir / "compare_error_outputs.py"
            results_file = script_dir / "test_results.json"

            if results_file.exists():
                cmd = [sys.executable, str(compare_script), str(results_file)]
                print(f"Running: {' '.join(cmd)}")
                result = subprocess.run(cmd, cwd=script_dir, check=True)

                if result.returncode == 0:
                    print("✓ Error comparison analysis completed successfully")

                    # Generate HTML report
                    report_script = script_dir / "error_conformance_report.py"
                    analysis_file = results_file.with_suffix('.analysis.json')

                    if analysis_file.exists():
                        cmd = [sys.executable, str(report_script), str(analysis_file)]
                        print(f"Running: {' '.join(cmd)}")
                        result = subprocess.run(cmd, cwd=script_dir, check=True)

                        if result.returncode == 0:
                            print("✓ HTML conformance report generated successfully")
                            print()
                            print("All tests completed! Check the following files:")
                            print(f"  - Results: {results_file}")
                            print(f"  - Analysis: {analysis_file}")
                            print(f"  - Report: {analysis_file.with_suffix('.html')}")
                        else:
                            print("✗ HTML report generation failed")
                    else:
                        print(f"✗ Analysis file {analysis_file} not found")
                else:
                    print("✗ Error comparison analysis failed")
            else:
                print(f"✗ Results file {results_file} not found")
        else:
            print("✗ Error consistency runner failed")

    except subprocess.CalledProcessError as e:
        print(f"✗ Command failed with return code {e.returncode}")
        print(f"Command: {' '.join(e.cmd)}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")


if __name__ == "__main__":
    main()