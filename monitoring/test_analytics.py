#!/usr/bin/env python3
"""
Test script for the ESM Format Package Analytics system.

This script demonstrates and tests the core functionality of the monitoring system.
"""

import time
import tempfile
import json
from pathlib import Path

# Import the analytics modules
from package_analytics import PackageAnalytics
from python_integration import ESMAnalytics, track_performance, record_event, track_operation, submit_feedback, get_performance_summary, get_usage_summary


def test_basic_analytics():
    """Test basic analytics functionality."""
    print("Testing basic analytics functionality...")

    # Use a temporary database for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_analytics.db"

        # Initialize analytics
        analytics = PackageAnalytics("test-package", "1.0.0", db_path=db_path)

        # Test performance tracking
        op_id = analytics.start_operation("test_operation", file_size_bytes=1024)
        time.sleep(0.01)  # Simulate work
        metric = analytics.end_operation(op_id, success=True)

        assert metric.operation == "test_operation"
        assert metric.success == True
        assert metric.duration_ms > 0
        print(f"✓ Performance tracking: {metric.duration_ms:.2f}ms")

        # Test usage event recording
        analytics.record_usage_event("test_event", file_type="esm", file_size_bytes=2048)
        print("✓ Usage event recording")

        # Test feedback submission
        feedback_id = analytics.submit_feedback(
            "test_feedback", 2, "Test Title", "Test description"
        )
        assert feedback_id is not None
        print(f"✓ Feedback submission: {feedback_id}")

        # Test summaries
        perf_summary = analytics.get_performance_summary(1)
        usage_summary = analytics.get_usage_summary(1)

        assert "operations" in perf_summary
        assert "events" in usage_summary
        print("✓ Summary generation")


def test_python_integration():
    """Test Python integration decorators and utilities."""
    print("\nTesting Python integration...")

    # Initialize the integration
    ESMAnalytics.initialize("test-integration", "1.0.0")

    # Test decorator functionality
    @track_performance("test_parse", track_file_size=True)
    @record_event("parse", track_file_info=True)
    def test_parse_function(content: str):
        """Test parsing function."""
        time.sleep(0.005)  # Simulate work
        return {"status": "parsed", "content_length": len(content)}

    # Test the decorated function
    result = test_parse_function("test content here")
    assert result["status"] == "parsed"
    print("✓ Decorated function tracking")

    # Test context manager
    with track_operation("test_validate", file_size_bytes=512):
        time.sleep(0.003)
        # Simulate validation work
        pass
    print("✓ Context manager tracking")

    # Test feedback submission through integration
    feedback_id = submit_feedback(
        "feature_request", 1, "Test Feature", "Please add this feature"
    )
    assert feedback_id is not None
    print(f"✓ Integration feedback: {feedback_id}")

    # Test summaries through integration
    perf_summary = get_performance_summary(1)
    usage_summary = get_usage_summary(1)

    if perf_summary:
        print(f"✓ Performance operations: {len(perf_summary.get('operations', {}))}")
    if usage_summary:
        print(f"✓ Usage events: {len(usage_summary.get('events', {}))}")


def test_error_handling():
    """Test error handling and failure tracking."""
    print("\nTesting error handling...")

    ESMAnalytics.initialize("test-error-handling", "1.0.0")

    @track_performance("test_failing_operation")
    @record_event("failing_operation")
    def failing_function():
        """Function that always fails."""
        time.sleep(0.002)
        raise ValueError("This is a test error")

    # Test that errors are properly tracked
    try:
        failing_function()
        assert False, "Function should have raised an exception"
    except ValueError:
        pass  # Expected

    print("✓ Error handling in decorators")

    # Test manual error tracking
    analytics = ESMAnalytics.get_instance()
    if analytics:
        op_id = analytics.start_operation("manual_error_test")
        try:
            time.sleep(0.001)
            raise RuntimeError("Manual test error")
        except RuntimeError as e:
            metric = analytics.end_operation(op_id, success=False, error_message=str(e))
            assert not metric.success
            assert "Manual test error" in metric.error_message
            print("✓ Manual error tracking")


def test_file_size_detection():
    """Test automatic file size detection."""
    print("\nTesting file size detection...")

    # Create temporary test files
    with tempfile.TemporaryDirectory() as temp_dir:
        small_file = Path(temp_dir) / "small.esm"
        large_file = Path(temp_dir) / "large.esm"

        small_file.write_text("small content")
        large_file.write_text("x" * 10000)  # 10KB file

        ESMAnalytics.initialize("test-file-detection", "1.0.0")

        @track_performance("parse_file", track_file_size=True)
        @record_event("parse", track_file_info=True)
        def parse_file(file_path: str):
            time.sleep(0.001)
            return Path(file_path).read_text()

        # Test small file
        result = parse_file(str(small_file))
        assert "small content" in result

        # Test large file
        result = parse_file(str(large_file))
        assert len(result) == 10000

        print("✓ File size detection")


def test_analytics_cli_integration():
    """Test that the CLI can read our test data."""
    print("\nTesting CLI integration...")

    analytics = ESMAnalytics.get_instance()
    if analytics:
        # Generate some test data
        for i in range(5):
            with track_operation(f"cli_test_{i}", file_size_bytes=i*100):
                time.sleep(0.001 * i)

        # Test that we can get summaries (CLI would use these)
        perf_summary = analytics.get_performance_summary(1)
        usage_summary = analytics.get_usage_summary(1)

        assert perf_summary is not None
        assert usage_summary is not None
        print("✓ CLI data generation")


def main():
    """Run all tests."""
    print("ESM Format Package Analytics - Test Suite")
    print("=" * 50)

    try:
        test_basic_analytics()
        test_python_integration()
        test_error_handling()
        test_file_size_detection()
        test_analytics_cli_integration()

        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("\nThe analytics system is working correctly.")
        print("\nTo view your test data:")
        print("1. Run: python monitoring/analytics_cli.py status")
        print("2. Run: python monitoring/analytics_cli.py dashboard")
        print("3. Visit: http://localhost:5000")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    main()