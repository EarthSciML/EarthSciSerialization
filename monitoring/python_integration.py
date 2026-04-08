"""
Python Integration for ESM Format Package Analytics

Provides decorators and utilities to easily integrate performance monitoring
and analytics into Python ESM format packages.
"""

import functools
import os
from typing import Callable, Any, Optional, Dict
from pathlib import Path

# Import from the analytics module
try:
    from .package_analytics import PackageAnalytics, create_context_manager
except ImportError:
    from package_analytics import PackageAnalytics, create_context_manager


class ESMAnalytics:
    """Easy-to-use analytics integration for ESM format packages."""

    _instance: Optional[PackageAnalytics] = None
    _enabled: bool = True

    @classmethod
    def initialize(cls, package_name: str, version: str,
                   enabled: Optional[bool] = None) -> PackageAnalytics:
        """Initialize analytics for a package."""
        if enabled is None:
            # Check environment variable
            enabled = os.getenv('ESM_ANALYTICS_ENABLED', '1').lower() in ('1', 'true', 'yes')

        cls._enabled = enabled
        if enabled:
            cls._instance = PackageAnalytics(package_name, version)
        return cls._instance

    @classmethod
    def get_instance(cls) -> Optional[PackageAnalytics]:
        """Get the current analytics instance."""
        return cls._instance if cls._enabled else None


def track_performance(operation_name: Optional[str] = None,
                     track_file_size: bool = False,
                     metadata: Optional[Dict[str, Any]] = None):
    """
    Decorator to track performance of a function.

    Args:
        operation_name: Name of the operation (defaults to function name)
        track_file_size: Whether to try to extract file size from function arguments
        metadata: Additional metadata to store with the metric
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            analytics = ESMAnalytics.get_instance()
            if not analytics:
                return func(*args, **kwargs)

            op_name = operation_name or func.__name__

            # Try to extract file size if requested
            file_size = None
            if track_file_size:
                file_size = _extract_file_size(args, kwargs)

            # Track the operation
            with create_context_manager(
                analytics.package_name,
                analytics.version
            )(op_name, file_size, metadata) as tracker:
                result = func(*args, **kwargs)
                return result

        return wrapper
    return decorator


def record_event(event_type: Optional[str] = None,
                track_file_info: bool = False,
                metadata: Optional[Dict[str, Any]] = None):
    """
    Decorator to record usage events.

    Args:
        event_type: Type of event (defaults to function name)
        track_file_info: Whether to extract file information from arguments
        metadata: Additional metadata to store with the event
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            analytics = ESMAnalytics.get_instance()
            if not analytics:
                return func(*args, **kwargs)

            event_name = event_type or func.__name__

            # Extract file info if requested
            file_type = None
            file_size = None
            if track_file_info:
                file_type, file_size = _extract_file_info(args, kwargs)

            try:
                result = func(*args, **kwargs)
                # Record successful event
                analytics.record_usage_event(
                    event_type=event_name,
                    file_type=file_type,
                    file_size_bytes=file_size,
                    success=True,
                    metadata=metadata
                )
                return result
            except Exception as e:
                # Record failed event
                analytics.record_usage_event(
                    event_type=event_name,
                    file_type=file_type,
                    file_size_bytes=file_size,
                    success=False,
                    error_type=type(e).__name__,
                    metadata={**(metadata or {}), 'error_message': str(e)}
                )
                raise

        return wrapper
    return decorator


def _extract_file_size(args: tuple, kwargs: dict) -> Optional[int]:
    """Extract file size from function arguments."""
    # Look for common file-related arguments
    for arg in args:
        if isinstance(arg, (str, Path)):
            try:
                path = Path(arg)
                if path.exists():
                    return path.stat().st_size
            except (OSError, TypeError):
                continue
        elif hasattr(arg, '__len__'):
            # Could be file content as string/bytes
            try:
                return len(arg)
            except TypeError:
                continue

    # Check kwargs for file paths
    for key, value in kwargs.items():
        if 'file' in key.lower() or 'path' in key.lower():
            if isinstance(value, (str, Path)):
                try:
                    path = Path(value)
                    if path.exists():
                        return path.stat().st_size
                except (OSError, TypeError):
                    continue

    return None


def _extract_file_info(args: tuple, kwargs: dict) -> tuple[Optional[str], Optional[int]]:
    """Extract file type and size from function arguments."""
    file_type = None
    file_size = None

    # Look for file paths in arguments
    for arg in args:
        if isinstance(arg, (str, Path)):
            try:
                path = Path(arg)
                if path.exists():
                    file_type = path.suffix.lower().lstrip('.')
                    file_size = path.stat().st_size
                    break
            except (OSError, TypeError):
                continue

    # If not found in args, check kwargs
    if file_type is None:
        for key, value in kwargs.items():
            if 'file' in key.lower() or 'path' in key.lower():
                if isinstance(value, (str, Path)):
                    try:
                        path = Path(value)
                        if path.exists():
                            file_type = path.suffix.lower().lstrip('.')
                            file_size = path.stat().st_size
                            break
                    except (OSError, TypeError):
                        continue

    # If still no file_size, try to get from content length
    if file_size is None:
        for arg in args:
            if hasattr(arg, '__len__'):
                try:
                    file_size = len(arg)
                    break
                except TypeError:
                    continue

    return file_type, file_size


# Context managers for manual tracking
def track_operation(operation_name: str, file_size_bytes: Optional[int] = None,
                   metadata: Optional[Dict[str, Any]] = None):
    """Context manager for manual operation tracking."""
    analytics = ESMAnalytics.get_instance()
    if not analytics:
        return _NoOpContextManager()

    return create_context_manager(
        analytics.package_name,
        analytics.version
    )(operation_name, file_size_bytes, metadata)


class _NoOpContextManager:
    """No-op context manager when analytics is disabled."""
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# Convenience functions
def submit_feedback(feedback_type: str, severity: int, title: str,
                   description: str, **kwargs) -> Optional[str]:
    """Submit feedback about the package."""
    analytics = ESMAnalytics.get_instance()
    if not analytics:
        return None

    return analytics.submit_feedback(
        feedback_type=feedback_type,
        severity=severity,
        title=title,
        description=description,
        **kwargs
    )


def get_performance_summary(days: int = 30) -> Optional[Dict[str, Any]]:
    """Get performance summary."""
    analytics = ESMAnalytics.get_instance()
    if not analytics:
        return None

    return analytics.get_performance_summary(days)


def get_usage_summary(days: int = 30) -> Optional[Dict[str, Any]]:
    """Get usage summary."""
    analytics = ESMAnalytics.get_instance()
    if not analytics:
        return None

    return analytics.get_usage_summary(days)


# Example usage demonstration
if __name__ == "__main__":
    import time

    # Initialize analytics
    ESMAnalytics.initialize("esm-format", "0.1.0")

    # Example functions with decorators
    @track_performance("parse_esm_file", track_file_size=True)
    @record_event("parse", track_file_info=True)
    def parse_file(file_path: str):
        """Example parsing function."""
        print(f"Parsing file: {file_path}")
        time.sleep(0.1)  # Simulate work
        return {"status": "parsed", "variables": 42}

    @track_performance("validate_model")
    @record_event("validate")
    def validate_model(model_data: dict):
        """Example validation function."""
        print("Validating model...")
        time.sleep(0.05)
        return model_data.get("variables", 0) > 0

    # Example usage
    print("Running example with analytics...")

    # Create a test file
    test_file = Path("/tmp/test.esm")
    test_file.write_text('{"version": "1.0", "model": {"variables": ["x", "y"]}}')

    # Use the decorated functions
    result = parse_file(str(test_file))
    is_valid = validate_model(result)

    # Manual tracking example
    with track_operation("custom_operation", file_size_bytes=1024):
        time.sleep(0.02)
        print("Custom operation completed")

    # Submit feedback
    feedback_id = submit_feedback(
        feedback_type="feature_request",
        severity=2,
        title="Add support for custom units",
        description="It would be great to support custom unit definitions"
    )
    print(f"Submitted feedback: {feedback_id}")

    # Get summaries
    perf_summary = get_performance_summary()
    usage_summary = get_usage_summary()

    if perf_summary:
        print(f"\nPerformance Summary:")
        print(f"Operations: {perf_summary}")

    if usage_summary:
        print(f"\nUsage Summary:")
        print(f"Events: {usage_summary}")

    # Clean up
    test_file.unlink()
    print("Example completed!")