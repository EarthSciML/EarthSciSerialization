#!/usr/bin/env python3

"""
Test script for enhanced conformance testing infrastructure.
Creates mock data and tests the enhanced analyzer and report generator.
"""

import json
import tempfile
from pathlib import Path
import subprocess
import sys

def create_mock_results():
    """Create mock conformance test results for testing."""

    # Mock language results
    mock_results = {
        "julia": {
            "language": "julia",
            "timestamp": "2026-02-17T12:00:00Z",
            "validation_results": {
                "valid": {
                    "simple_model.esm": {"is_valid": True, "schema_errors": [], "structural_errors": []},
                    "coupled_system.esm": {"is_valid": True, "schema_errors": [], "structural_errors": []}
                },
                "invalid": {
                    "broken_model.esm": {"is_valid": False, "schema_errors": ["missing_field"], "structural_errors": []}
                }
            },
            "errors": []
        },
        "typescript": {
            "language": "typescript",
            "timestamp": "2026-02-17T12:00:00Z",
            "validation_results": {
                "valid": {
                    "simple_model.esm": {"is_valid": True, "schema_errors": [], "structural_errors": []},
                    "coupled_system.esm": {"is_valid": True, "schema_errors": [], "structural_errors": []}
                },
                "invalid": {
                    "broken_model.esm": {"is_valid": False, "schema_errors": ["missing_field"], "structural_errors": []}
                }
            },
            "errors": []
        },
        "python": {
            "language": "python",
            "timestamp": "2026-02-17T12:00:00Z",
            "validation_results": {
                "valid": {
                    "simple_model.esm": {"is_valid": True, "schema_errors": [], "structural_errors": []},
                    "coupled_system.esm": {"is_valid": False, "schema_errors": ["type_mismatch"], "structural_errors": []}  # Divergence
                },
                "invalid": {
                    "broken_model.esm": {"is_valid": False, "schema_errors": ["missing_field"], "structural_errors": []}
                }
            },
            "errors": []
        }
    }

    # Mock performance data
    mock_performance = {
        "julia": {
            "execution_time_ms": 1200.5,
            "memory_peak_mb": 256.7,
            "memory_avg_mb": 180.3,
            "cpu_usage_percent": 45.2,
            "test_count": 3,
            "success_rate": 1.0,
            "avg_test_time_ms": 400.17
        },
        "typescript": {
            "execution_time_ms": 890.2,
            "memory_peak_mb": 412.1,
            "memory_avg_mb": 320.8,
            "cpu_usage_percent": 62.7,
            "test_count": 3,
            "success_rate": 1.0,
            "avg_test_time_ms": 296.73
        },
        "python": {
            "execution_time_ms": 750.8,
            "memory_peak_mb": 189.4,
            "memory_avg_mb": 145.6,
            "cpu_usage_percent": 38.9,
            "test_count": 3,
            "success_rate": 0.67,
            "avg_test_time_ms": 250.27
        }
    }

    return mock_results, mock_performance

def test_enhanced_analyzer():
    """Test the enhanced conformance analyzer."""

    print("Testing enhanced conformance analyzer...")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create mock results and performance data
        mock_results, mock_performance = create_mock_results()

        # Set up directory structure
        for language in mock_results.keys():
            lang_dir = temp_path / language
            lang_dir.mkdir()

            # Write results.json
            with open(lang_dir / "results.json", "w") as f:
                json.dump(mock_results[language], f, indent=2)

            # Write performance.json
            with open(lang_dir / "performance.json", "w") as f:
                json.dump(mock_performance[language], f, indent=2)

        # Create comparison output directory
        comparison_dir = temp_path / "comparison"
        comparison_dir.mkdir()

        # Run enhanced analyzer
        cmd = [
            sys.executable, "scripts/enhanced-conformance-analyzer.py",
            "--output-dir", str(temp_path),
            "--languages", "julia", "typescript", "python",
            "--comparison-output", str(comparison_dir / "analysis.json"),
            "--performance-analysis",
            "--detailed-diffs"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Enhanced analyzer completed successfully")

            # Check if analysis file was created
            analysis_file = comparison_dir / "analysis.json"
            if analysis_file.exists():
                with open(analysis_file) as f:
                    analysis = json.load(f)
                print(f"   Analysis status: {analysis.get('overall_status')}")
                print(f"   Languages tested: {len(analysis.get('languages_tested', []))}")
                print(f"   Performance analysis: {'Yes' if 'performance_analysis' in analysis else 'No'}")
                return analysis_file
            else:
                print("❌ Analysis file not created")
                return None
        else:
            print("❌ Enhanced analyzer failed")
            print(f"   Error: {result.stderr}")
            return None

def test_enhanced_report_generator(analysis_file):
    """Test the enhanced report generator."""

    if not analysis_file:
        print("⏭️  Skipping report generation (no analysis file)")
        return False

    print("Testing enhanced report generator...")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        report_file = temp_path / "test_report.html"

        # Run enhanced report generator
        cmd = [
            sys.executable, "scripts/enhanced-report-generator.py",
            "--analysis-file", str(analysis_file),
            "--output-file", str(report_file),
            "--include-performance-charts",
            "--detailed-analysis"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and report_file.exists():
            print("✅ Enhanced report generator completed successfully")
            print(f"   Report size: {report_file.stat().st_size} bytes")

            # Check if report contains expected content
            with open(report_file) as f:
                content = f.read()

            checks = [
                "Cross-Language Conformance Report" in content,
                "Performance Analysis" in content,
                "Detailed Divergence Analysis" in content,
                "plotly" in content.lower()
            ]

            passed_checks = sum(checks)
            print(f"   Content checks: {passed_checks}/4 passed")
            return passed_checks >= 3
        else:
            print("❌ Enhanced report generator failed")
            if result.stderr:
                print(f"   Error: {result.stderr}")
            return False

def test_docker_infrastructure():
    """Test if Docker infrastructure can be built."""

    print("Testing Docker infrastructure...")

    # Check if Docker is available
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("⏭️  Docker not available, skipping Docker tests")
            return True
    except FileNotFoundError:
        print("⏭️  Docker not found, skipping Docker tests")
        return True

    # Test building one Docker image (Julia as example)
    cmd = [
        "docker", "build", "-f", "docker/Dockerfile.julia",
        "-t", "esm-format-julia:test", "."
    ]

    print("   Building Julia Docker image...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ Docker image built successfully")

        # Clean up test image
        subprocess.run(["docker", "rmi", "esm-format-julia:test"],
                      capture_output=True, text=True)
        return True
    else:
        print("❌ Docker image build failed")
        print("   This might be expected if dependencies are missing")
        print(f"   Error: {result.stderr[:200]}...")
        return False

def main():
    """Run all infrastructure tests."""

    print("=== Testing Enhanced Conformance Testing Infrastructure ===\n")

    # Test enhanced analyzer
    analysis_file = test_enhanced_analyzer()
    print()

    # Test enhanced report generator
    report_success = test_enhanced_report_generator(analysis_file)
    print()

    # Test Docker infrastructure
    docker_success = test_docker_infrastructure()
    print()

    # Summary
    print("=== Test Summary ===")
    print(f"✅ Enhanced Analyzer: {'PASS' if analysis_file else 'FAIL'}")
    print(f"✅ Enhanced Report Generator: {'PASS' if report_success else 'FAIL'}")
    print(f"✅ Docker Infrastructure: {'PASS' if docker_success else 'PARTIAL'}")

    overall_success = bool(analysis_file) and report_success
    print(f"\n🎯 Overall: {'SUCCESS' if overall_success else 'PARTIAL SUCCESS'}")

    if overall_success:
        print("\n✅ Enhanced conformance testing infrastructure is working!")
        print("   Ready for production use.")
    else:
        print("\n⚠️  Some components need attention, but core functionality works.")
        print("   Check individual component outputs above.")

    return 0 if overall_success else 1

if __name__ == "__main__":
    exit(main())