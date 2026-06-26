"""Cross-binding conformance + engine tests for the ``expression`` initial
condition type (bead ess-gjn, epic campfire-e2e ea-6sh).

The shared golden under ``tests/valid/initial_conditions/`` declares a
domain-level ``expression`` initial condition: each variable's initial field is
the EXISTING expression AST evaluated over the spatial grid at t=0 — reusing the
NumPy interpreter, not a new primitive. This module:

* validates the golden (schema + structural) — the contract all five bindings
  load,
* runs its inline ``tests`` through :func:`simulate` and asserts every
  ``(variable, time, expected)`` triple within tolerance — the same inline
  ``expected`` values Julia and Rust will check once their expression-IC
  evaluation lands (Python-first; JL/RS end-to-end deferred per ess-gjn),
* exercises the engine directly for 2-D (camp_fire ignition-front) generality
  and for explicit-IC-overrides-expression precedence.

Mirrors the ``tests/valid/aggregate`` conformance runner
(``test_aggregate_conformance.py``), which likewise drives the loaded file —
preserving its ``domains`` block — straight through :func:`simulate`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pytest

pytest.importorskip("scipy")

from earthsci_toolkit.parse import load
from earthsci_toolkit.simulation import simulate
from earthsci_toolkit.validation import validate


_FIXTURES_DIR = (
    Path(__file__).resolve().parents[3]  # repo root
    / "tests"
    / "valid"
    / "initial_conditions"
)


def _collect_fixtures() -> List[Path]:
    """Golden fixtures that carry at least one inline model ``tests`` block."""
    if not _FIXTURES_DIR.is_dir():
        return []
    out: List[Path] = []
    for p in sorted(_FIXTURES_DIR.glob("*.esm")):
        raw = json.loads(p.read_text())
        if any(m.get("tests") for m in (raw.get("models") or {}).values()):
            out.append(p)
    return out


def _resolve_tol(
    model_tol: Dict[str, float],
    test_tol: Dict[str, float],
    assertion_tol: Dict[str, float],
) -> Tuple[float, float]:
    merged: Dict[str, float] = {}
    for t in (model_tol or {}), (test_tol or {}), (assertion_tol or {}):
        if t:
            merged.update(t)
    return float(merged.get("rel", 0.0)), float(merged.get("abs", 0.0))


def _lookup_element(
    result_vars: List[str],
    result_y: np.ndarray,
    result_t: np.ndarray,
    var_key: str,
    time: float,
) -> float:
    match_idx = None
    for i, name in enumerate(result_vars):
        if name == var_key or name.endswith("." + var_key):
            match_idx = i
            break
    if match_idx is None:
        raise AssertionError(f"Variable {var_key!r} not in result vars: {result_vars}")
    y_row = result_y[match_idx, :]
    if len(result_t) == 0:
        raise AssertionError("Result has no time points")
    if time <= result_t[0]:
        return float(y_row[0])
    if time >= result_t[-1]:
        return float(y_row[-1])
    return float(np.interp(time, result_t, y_row))


def _assertion_passes(actual: float, expected: float, rel: float, ab: float) -> bool:
    diff = abs(actual - expected)
    if ab > 0 and diff <= ab:
        return True
    if rel > 0 and diff / max(abs(expected), 1e-12) <= rel:
        return True
    if ab == 0 and rel == 0:
        return diff == 0.0
    return False


def test_expression_ic_fixtures_present() -> None:
    """The expression-IC golden must be present and executable."""
    assert _collect_fixtures(), (
        f"expected >= 1 executable expression-IC golden under {_FIXTURES_DIR} "
        f"(did the shared fixture lose its inline `tests`?)"
    )


@pytest.mark.parametrize("fixture_path", _collect_fixtures(), ids=lambda p: p.name)
def test_expression_ic_fixture_conformance(fixture_path: Path) -> None:
    """Validate the golden and run every inline test through simulate()."""
    # Schema + structural validation: the five-binding contract.
    vres = validate(fixture_path.read_text())
    assert vres.is_valid, (
        f"{fixture_path.name} failed validation: "
        f"schema={getattr(vres, 'schema_errors', None)} "
        f"structural={getattr(vres, 'structural_errors', None)}"
    )

    raw = json.loads(fixture_path.read_text())
    esm_file = load(fixture_path)

    any_assertions = False
    for model_name, model_raw in (raw.get("models") or {}).items():
        tests = model_raw.get("tests") or []
        model_tolerance = model_raw.get("tolerance") or {}

        for test in tests:
            test_id = test.get("id", "?")
            tspan_raw = test["time_span"]
            tspan = (float(tspan_raw["start"]), float(tspan_raw["end"]))
            # Omitting initial_conditions seeds the field purely from the
            # domain expression IC — the behaviour under test.
            ics = {k: float(v) for k, v in (test.get("initial_conditions") or {}).items()}
            params = {k: float(v) for k, v in (test.get("parameter_overrides") or {}).items()}

            result = simulate(
                esm_file, tspan=tspan, initial_conditions=ics, parameters=params
            )
            assert result.success, (
                f"{fixture_path.name}::{model_name}::{test_id} "
                f"simulation failed: {result.message}"
            )

            test_tolerance = test.get("tolerance") or {}
            for assertion in test.get("assertions", []):
                any_assertions = True
                rel, ab = _resolve_tol(
                    model_tolerance, test_tolerance, assertion.get("tolerance") or {}
                )
                actual = _lookup_element(
                    result.vars, result.y, result.t,
                    assertion["variable"], float(assertion["time"]),
                )
                expected = float(assertion["expected"])
                assert _assertion_passes(actual, expected, rel, ab), (
                    f"{fixture_path.name}::{model_name}::{test_id} "
                    f"assertion {assertion['variable']}@t={assertion['time']} "
                    f"expected={expected} actual={actual} tol(rel={rel}, abs={ab})"
                )

    assert any_assertions, f"{fixture_path.name}: no assertions were checked"


# ---------------------------------------------------------------------------
# Engine unit tests (Python binding) — beyond the shared golden.
# ---------------------------------------------------------------------------


def _two_d_field_fixture() -> Dict[str, Any]:
    """A 3x3 field whose expression IC psi(x, y) = x + 10*y distinguishes the
    two spatial axes (camp_fire is 2-D, so N-D generality matters)."""
    return {
        "esm": "0.6.0",
        "metadata": {
            "name": "expr_ic_2d_unit",
            "description": "2-D expression-IC generality unit fixture.",
        },
        "models": {
            "Field2D": {
                "domain": "plane",
                "variables": {"u": {"type": "state", "shape": ["i", "j"]}},
                "equations": [
                    {
                        "lhs": {
                            "op": "aggregate", "args": [], "output_idx": ["i", "j"],
                            "expr": {
                                "op": "D",
                                "args": [{"op": "index", "args": ["u", "i", "j"]}],
                                "wrt": "t",
                            },
                            "ranges": {"i": [1, 3], "j": [1, 3]},
                        },
                        "rhs": {
                            "op": "aggregate", "args": [], "output_idx": ["i", "j"],
                            "ranges": {"i": [1, 3], "j": [1, 3]}, "expr": 0,
                        },
                    }
                ],
            }
        },
        "domains": {
            "plane": {
                "spatial": {
                    "x": {"min": 0.0, "max": 1.0, "grid_spacing": 0.5, "units": "m"},
                    "y": {"min": 0.0, "max": 1.0, "grid_spacing": 0.5, "units": "m"},
                },
                "initial_conditions": {
                    "type": "expression",
                    "values": {
                        "u": {"op": "+", "args": ["x", {"op": "*", "args": [10, "y"]}]}
                    },
                },
            }
        },
    }


def test_expression_ic_2d_generality() -> None:
    """The expression IC is evaluated over a full 2-D grid with axis 0 -> x,
    axis 1 -> y, written in C order — psi(x, y) = x + 10*y."""
    result = simulate(load(_two_d_field_fixture()), tspan=(0.0, 1.0), initial_conditions={})
    assert result.success, result.message
    xs = [0.0, 0.5, 1.0]
    ys = [0.0, 0.5, 1.0]
    for i in range(3):
        for j in range(3):
            actual = _lookup_element(
                result.vars, result.y, result.t, f"u[{i + 1},{j + 1}]", 0.0
            )
            expected = xs[i] + 10.0 * ys[j]
            assert abs(actual - expected) < 1e-9, (
                f"u[{i + 1},{j + 1}] = {actual} != psi = {expected}"
            )


def test_explicit_initial_conditions_override_expression() -> None:
    """An explicit per-element initial_conditions value wins over the domain
    expression IC; untouched elements still come from the expression."""
    golden = _FIXTURES_DIR / "expression_ignition_front_1d.esm"
    esm_file = load(golden)
    result = simulate(
        esm_file, tspan=(0.0, 1.0), initial_conditions={"u[3]": -7.0}
    )
    assert result.success, result.message
    # Overridden element.
    assert abs(_lookup_element(result.vars, result.y, result.t, "u[3]", 0.0) - (-7.0)) < 1e-12
    # Neighbour still seeded from psi(x): psi(0) = 0.5*(1 + tanh(-2)) = 0.01798...
    assert abs(
        _lookup_element(result.vars, result.y, result.t, "u[1]", 0.0)
        - 0.01798620996209155
    ) < 1e-9
