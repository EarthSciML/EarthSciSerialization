"""Round-trip coverage for the `call` op + `registered_functions` registry.

Introduced in gt-p3ep. The cross-binding fixtures live in
``tests/registered_funcs/`` and exercise the calling contract — handler
bodies are supplied by the host runtime through a handler registry
(esm-spec §4.4 / §9.2).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from earthsci_toolkit import load, save

_FIXTURE_DIR = Path(__file__).resolve().parents[3] / "tests" / "registered_funcs"

_FIXTURES = [
    "pure_math.esm",
    "one_d_interpolator.esm",
    "two_d_table_lookup.esm",
]


@pytest.mark.parametrize("fixture", _FIXTURES)
def test_registered_funcs_round_trip(fixture: str) -> None:
    """load → save → load → save must be idempotent on call + registered_functions."""
    content = (_FIXTURE_DIR / fixture).read_text()
    parsed = load(content)
    first = save(parsed)
    reloaded = load(first)
    second = save(reloaded)
    assert json.loads(first) == json.loads(second), (
        f"serializer is not idempotent on {fixture}"
    )


def test_call_op_handler_id_preserved() -> None:
    """The `call` node's handler_id must survive a parse → serialize round-trip."""
    content = (_FIXTURE_DIR / "pure_math.esm").read_text()
    parsed = load(content)
    model = parsed.models["PureMathCall"]
    rhs = model.equations[0].rhs
    assert rhs.op == "call"
    assert rhs.handler_id == "sq"
    # And it survives a round-trip:
    payload = json.loads(save(parsed))
    rhs_json = payload["models"]["PureMathCall"]["equations"][0]["rhs"]
    assert rhs_json["op"] == "call"
    assert rhs_json["handler_id"] == "sq"


def test_registered_function_arg_units_null_survives() -> None:
    """A ``null`` entry inside ``arg_units`` must survive a round-trip."""
    content = (_FIXTURE_DIR / "two_d_table_lookup.esm").read_text()
    parsed = load(content)
    r_c = parsed.registered_functions["r_c_wesely"]
    assert r_c.arg_units is not None
    assert r_c.arg_units[0] == "K"
    assert r_c.arg_units[1] == "m^2/m^2"
    assert r_c.arg_units[2] is None
    # Round-trip preserves the null slot:
    payload = json.loads(save(parsed))
    arg_units = payload["registered_functions"]["r_c_wesely"]["arg_units"]
    assert arg_units == ["K", "m^2/m^2", None]


def test_missing_registered_function_is_diagnosed() -> None:
    """A ``call`` that references an unknown ``handler_id`` must be rejected
    by ``validate`` with a ``missing_registered_function`` diagnostic."""
    from earthsci_toolkit.parse import SchemaValidationError

    bogus = {
        "esm": "0.1.0",
        "metadata": {"name": "bogus"},
        "registered_functions": {
            "declared": {
                "id": "declared",
                "signature": {"arg_count": 1},
            }
        },
        "models": {
            "M": {
                "variables": {"x": {"type": "parameter", "default": 1.0},
                              "y": {"type": "state"}},
                "equations": [{
                    "lhs": {"op": "D", "args": ["y"], "wrt": "t"},
                    "rhs": {"op": "call", "handler_id": "undeclared", "args": ["x"]},
                }],
            }
        },
    }
    with pytest.raises(SchemaValidationError) as exc:
        load(json.dumps(bogus))
    assert "missing_registered_function" in str(exc.value) or \
        any("missing_registered_function" in e for e in (exc.value.errors or []))
