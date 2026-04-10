"""Tests for subsystem reference resolution in load()."""

import json
import os
import tempfile

import pytest

from earthsci_toolkit import load
from earthsci_toolkit.parse import (
    CircularReferenceError,
    SubsystemRefError,
    resolve_subsystem_refs,
)


def _write(path: str, payload: dict) -> None:
    with open(path, "w") as f:
        json.dump(payload, f)


def test_load_resolves_local_subsystem_ref():
    with tempfile.TemporaryDirectory() as tmp:
        sub_path = os.path.join(tmp, "inner.esm.json")
        _write(sub_path, {
            "esm": "0.1.0",
            "metadata": {"name": "inner"},
            "models": {
                "Inner": {
                    "variables": {
                        "x": {"type": "state", "default": 1.0},
                    },
                    "equations": [],
                },
            },
        })

        main_path = os.path.join(tmp, "main.esm.json")
        _write(main_path, {
            "esm": "0.1.0",
            "metadata": {"name": "main"},
            "models": {
                "Outer": {
                    "variables": {},
                    "equations": [],
                    "subsystems": {
                        "Inner": {"ref": "./inner.esm.json"},
                    },
                },
            },
        })

        loaded = load(main_path)
        outer = loaded.models["Outer"]
        assert "Inner" in outer.subsystems
        inner = outer.subsystems["Inner"]
        # After resolution we should have the typed model with x as a state var
        assert hasattr(inner, "variables")
        assert "x" in inner.variables


def test_load_raises_for_missing_local_ref():
    with tempfile.TemporaryDirectory() as tmp:
        main_path = os.path.join(tmp, "main.esm.json")
        _write(main_path, {
            "esm": "0.1.0",
            "metadata": {"name": "main"},
            "models": {
                "Outer": {
                    "variables": {},
                    "equations": [],
                    "subsystems": {
                        "Missing": {"ref": "./does-not-exist.esm.json"},
                    },
                },
            },
        })

        with pytest.raises(SubsystemRefError):
            load(main_path)


def test_circular_reference_detection():
    with tempfile.TemporaryDirectory() as tmp:
        a_path = os.path.join(tmp, "a.esm.json")
        b_path = os.path.join(tmp, "b.esm.json")
        _write(a_path, {
            "esm": "0.1.0",
            "metadata": {"name": "a"},
            "models": {
                "A": {
                    "variables": {},
                    "equations": [],
                    "subsystems": {"Cycle": {"ref": "./b.esm.json"}},
                },
            },
        })
        _write(b_path, {
            "esm": "0.1.0",
            "metadata": {"name": "b"},
            "models": {
                "B": {
                    "variables": {},
                    "equations": [],
                    "subsystems": {"Cycle": {"ref": "./a.esm.json"}},
                },
            },
        })

        main_path = os.path.join(tmp, "main.esm.json")
        _write(main_path, {
            "esm": "0.1.0",
            "metadata": {"name": "main"},
            "models": {
                "Root": {
                    "variables": {},
                    "equations": [],
                    "subsystems": {"Start": {"ref": "./a.esm.json"}},
                },
            },
        })

        with pytest.raises(CircularReferenceError):
            load(main_path)
