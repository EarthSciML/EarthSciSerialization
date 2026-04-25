"""Tests for the optional monitoring shim.

These run with or without the ``monitoring`` companion package installed —
they verify that the binding works either way (fault-tolerant no-op path).
"""

from earthsci_toolkit import _monitoring
from earthsci_toolkit._monitoring import (
    is_monitoring_available,
    record_event,
    track_operation,
    track_performance,
)


def test_track_performance_is_transparent():
    @track_performance("unit-test-op")
    def square(x):
        return x * x

    assert square(5) == 25
    assert square.__name__ == "square" or is_monitoring_available()


def test_record_event_is_transparent():
    calls = []

    @record_event("unit-test-evt")
    def greet(name):
        calls.append(name)
        return f"hi {name}"

    assert greet("world") == "hi world"
    assert calls == ["world"]


def test_track_operation_context_manager():
    with track_operation("unit-test-ctx") as handle:
        # No-op handle must support the context protocol even without monitoring.
        assert handle is not None or not is_monitoring_available()


def test_initialize_if_enabled_is_idempotent(monkeypatch):
    monkeypatch.setenv("ESM_ANALYTICS_ENABLED", "0")
    # Must not raise, regardless of whether monitoring is installed.
    _monitoring.initialize_if_enabled("pkg", "0.0.0")
    _monitoring.initialize_if_enabled("pkg", "0.0.0")


def test_load_works_end_to_end():
    """Public load() is decorated — ensure it still returns a valid object."""
    from pathlib import Path

    from earthsci_toolkit import load

    fixture = (
        Path(__file__).resolve().parents[3]
        / "tests"
        / "valid"
        / "data_loaders_comprehensive.esm"
    )
    if not fixture.exists():
        # Fixture not present in this checkout — skip rather than fabricate one.
        import pytest

        pytest.skip(f"fixture missing: {fixture}")

    esm = load(fixture)
    assert esm is not None
