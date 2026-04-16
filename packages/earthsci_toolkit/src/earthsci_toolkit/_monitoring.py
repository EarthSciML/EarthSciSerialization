"""
Fault-tolerant shim around the optional ``monitoring`` companion package.

The ``monitoring`` package is an optional dependency. When it is installed,
:func:`track_performance` and :func:`record_event` delegate to the real
decorators from :mod:`monitoring.python_integration`. When it is not
installed, they collapse to transparent no-op decorators, so the binding
works unchanged.

Analytics collection is also gated by the ``ESM_ANALYTICS_ENABLED``
environment variable (default: on). Set ``ESM_ANALYTICS_ENABLED=0`` to
force no-op mode even when monitoring is installed.
"""

from __future__ import annotations

import os

try:
    from monitoring.python_integration import (  # type: ignore[import-not-found]
        ESMAnalytics as _ESMAnalytics,
        record_event as _record_event,
        track_operation as _track_operation,
        track_performance as _track_performance,
    )

    _MONITORING_AVAILABLE = True
except ImportError:
    _MONITORING_AVAILABLE = False

    def _track_performance(*_args, **_kwargs):
        def decorator(fn):
            return fn

        return decorator

    def _record_event(*_args, **_kwargs):
        def decorator(fn):
            return fn

        return decorator

    class _NoOpContextManager:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

    def _track_operation(*_args, **_kwargs):
        return _NoOpContextManager()

    class _ESMAnalytics:  # type: ignore[no-redef]
        @classmethod
        def initialize(cls, *_args, **_kwargs):
            return None

        @classmethod
        def get_instance(cls):
            return None


def _analytics_enabled() -> bool:
    return os.getenv("ESM_ANALYTICS_ENABLED", "1").lower() in ("1", "true", "yes")


def is_monitoring_available() -> bool:
    """Return True if the optional ``monitoring`` package is importable."""
    return _MONITORING_AVAILABLE


def initialize_if_enabled(package_name: str, version: str) -> None:
    """Initialize analytics collection iff monitoring is installed AND enabled.

    Safe to call multiple times. A no-op when monitoring is absent.
    """
    if not _MONITORING_AVAILABLE or not _analytics_enabled():
        return
    if _ESMAnalytics.get_instance() is None:
        _ESMAnalytics.initialize(package_name, version)


track_performance = _track_performance
record_event = _record_event
track_operation = _track_operation

__all__ = [
    "initialize_if_enabled",
    "is_monitoring_available",
    "record_event",
    "track_operation",
    "track_performance",
]
