"""Unit tests for the discretize() pipeline (RFC §11, gt-57nn).

Mirrors ``packages/EarthSciSerialization.jl/test/discretize_test.jl`` at
commit ``5849c525`` (gt-gbs2) — the §11 subset. DAE handling (RFC §12,
gt-q7sh) is a separate bead per binding and is not covered here.
"""

from __future__ import annotations

import copy
import json

import pytest

from earthsci_toolkit import RuleEngineError, discretize
from earthsci_toolkit.canonicalize import canonical_json
from earthsci_toolkit.parse import _parse_expression


def _scalar_ode_esm():
    return {
        "esm": "0.2.0",
        "metadata": {
            "name": "scalar_ode",
            "description": "dx/dt = -k * x",
        },
        "models": {
            "M": {
                "variables": {
                    "x": {"type": "state", "default": 1.0, "units": "1"},
                    "k": {"type": "parameter", "default": 0.5, "units": "1/s"},
                },
                "equations": [
                    {
                        "lhs": {"op": "D", "args": ["x"], "wrt": "t"},
                        "rhs": {
                            "op": "*",
                            "args": [
                                {"op": "-", "args": ["k"]},
                                "x",
                            ],
                        },
                    },
                ],
            },
        },
    }


def _heat_1d_esm(with_rule: bool = True):
    esm = {
        "esm": "0.2.0",
        "metadata": {"name": "heat_1d"},
        "grids": {
            "gx": {
                "family": "cartesian",
                "dimensions": [
                    {"name": "i", "size": 8, "periodic": True, "spacing": "uniform"},
                ],
            },
        },
        "models": {
            "M": {
                "grid": "gx",
                "variables": {
                    "u": {
                        "type": "state",
                        "default": 0.0,
                        "units": "1",
                        "shape": ["i"],
                        "location": "cell_center",
                    },
                },
                "equations": [
                    {
                        "lhs": {"op": "D", "args": ["u"], "wrt": "t"},
                        "rhs": {"op": "grad", "args": ["u"], "dim": "i"},
                    },
                ],
            },
        },
    }
    if with_rule:
        esm["rules"] = [
            {
                "name": "centered_grad",
                "pattern": {"op": "grad", "args": ["$u"], "dim": "$x"},
                "replacement": {
                    "op": "+",
                    "args": [
                        {
                            "op": "-",
                            "args": [
                                {
                                    "op": "index",
                                    "args": [
                                        "$u",
                                        {"op": "-", "args": ["$x", 1]},
                                    ],
                                },
                            ],
                        },
                        {
                            "op": "index",
                            "args": [
                                "$u",
                                {"op": "+", "args": ["$x", 1]},
                            ],
                        },
                    ],
                },
            },
        ]
    return esm


# ---------------------------------------------------------------------------
# Acceptance tests (RFC §11)
# ---------------------------------------------------------------------------


def test_runs_end_to_end_on_scalar_ode():
    esm = _scalar_ode_esm()
    input_copy = copy.deepcopy(esm)
    out = discretize(esm)
    assert isinstance(out, dict)
    assert "discretized_from" in out["metadata"]
    assert out["metadata"]["discretized_from"]["name"] == "scalar_ode"
    assert "discretized" in out["metadata"]["tags"]
    # Input must not be mutated.
    assert esm == input_copy
    assert "discretized_from" not in esm["metadata"]


def test_runs_end_to_end_on_1d_pde_with_matching_rule():
    esm = _heat_1d_esm(with_rule=True)
    out = discretize(esm)
    rhs = out["models"]["M"]["equations"][0]["rhs"]
    rhs_json = json.dumps(rhs)
    assert '"grad"' not in rhs_json
    assert '"index"' in rhs_json


def test_determinism_two_calls_byte_identical():
    esm = _heat_1d_esm(with_rule=True)
    a = discretize(esm)
    b = discretize(esm)
    rhs_a = a["models"]["M"]["equations"][0]["rhs"]
    rhs_b = b["models"]["M"]["equations"][0]["rhs"]
    assert canonical_json(_parse_expression(rhs_a)) == canonical_json(
        _parse_expression(rhs_b)
    )
    assert a["metadata"]["discretized_from"] == b["metadata"]["discretized_from"]


def test_output_reparses_through_parse_expression():
    esm = _scalar_ode_esm()
    out = discretize(esm)
    rhs = out["models"]["M"]["equations"][0]["rhs"]
    parsed = _parse_expression(rhs)
    # parse_expression returns ExprNode or a leaf; either way it parses.
    assert parsed is not None


def test_e_unrewritten_pde_op_on_unmatched_pde_op():
    esm = _heat_1d_esm(with_rule=False)
    with pytest.raises(RuleEngineError) as exc_info:
        discretize(esm)
    assert exc_info.value.code == "E_UNREWRITTEN_PDE_OP"


def test_strict_unrewritten_false_stamps_passthrough_and_retains_op():
    esm = _heat_1d_esm(with_rule=False)
    out = discretize(esm, strict_unrewritten=False)
    eqn = out["models"]["M"]["equations"][0]
    assert eqn["passthrough"] is True
    assert '"grad"' in json.dumps(eqn["rhs"])


def test_passthrough_true_on_input_skips_coverage_check():
    esm = _heat_1d_esm(with_rule=False)
    esm["models"]["M"]["equations"][0]["passthrough"] = True
    out = discretize(esm)  # default strict_unrewritten=True is fine
    assert out["models"]["M"]["equations"][0]["passthrough"] is True


def test_bc_value_canonicalization_no_rules():
    esm = {
        "esm": "0.2.0",
        "metadata": {"name": "bc_plain"},
        "models": {
            "M": {
                "variables": {
                    "u": {"type": "state", "default": 0.0, "units": "1"},
                },
                "equations": [
                    {
                        "lhs": {"op": "D", "args": ["u"], "wrt": "t"},
                        "rhs": 0.0,
                    },
                ],
                "boundary_conditions": {
                    "u_dirichlet_xmin": {
                        "variable": "u",
                        "side": "xmin",
                        "kind": "dirichlet",
                        # 1 + 0 should canonicalize to 1.
                        "value": {"op": "+", "args": [1, 0]},
                    },
                },
            },
        },
    }
    out = discretize(esm)
    bc_val = out["models"]["M"]["boundary_conditions"]["u_dirichlet_xmin"]["value"]
    assert bc_val == 1


def test_max_passes_surfaces_e_rules_not_converged():
    esm = {
        "esm": "0.2.0",
        "metadata": {"name": "loop"},
        "rules": [
            {
                "name": "never",
                "pattern": "$a",
                "replacement": {"op": "+", "args": ["$a", 1]},
            },
        ],
        "models": {
            "M": {
                "variables": {
                    "y": {"type": "state", "default": 0.0, "units": "1"},
                },
                "equations": [
                    {
                        "lhs": {"op": "D", "args": ["y"], "wrt": "t"},
                        "rhs": "y",
                    },
                ],
            },
        },
    }
    with pytest.raises(RuleEngineError) as exc_info:
        discretize(esm, max_passes=3)
    assert exc_info.value.code == "E_RULES_NOT_CONVERGED"


# ---------------------------------------------------------------------------
# Extra python-side coverage
# ---------------------------------------------------------------------------


def test_per_model_rules_merge_with_top_level():
    """Model-local rules extend top-level rules (Julia parity)."""
    esm = _heat_1d_esm(with_rule=False)
    # Move the rule from top level to model-local.
    esm["models"]["M"]["rules"] = [
        {
            "name": "centered_grad",
            "pattern": {"op": "grad", "args": ["$u"], "dim": "$x"},
            "replacement": {"op": "index", "args": ["$u", "$x"]},
        },
    ]
    out = discretize(esm)
    rhs = out["models"]["M"]["equations"][0]["rhs"]
    assert '"grad"' not in json.dumps(rhs)


def test_metadata_without_name_still_records_empty_provenance():
    esm = {
        "esm": "0.2.0",
        "models": {
            "M": {
                "variables": {"x": {"type": "state", "default": 0.0, "units": "1"}},
                "equations": [
                    {
                        "lhs": {"op": "D", "args": ["x"], "wrt": "t"},
                        "rhs": 0.0,
                    },
                ],
            },
        },
    }
    out = discretize(esm)
    assert out["metadata"]["discretized_from"] == {}
    assert "discretized" in out["metadata"]["tags"]


def test_equation_lhs_canonicalized_without_rewrite():
    """LHS is canonicalized only — rules do not fire on LHS."""
    esm = {
        "esm": "0.2.0",
        "metadata": {"name": "lhs_canon"},
        "rules": [
            {
                "name": "drop_D",
                "pattern": {"op": "D", "args": ["$x"], "wrt": "t"},
                "replacement": "$x",
            },
        ],
        "models": {
            "M": {
                "variables": {"x": {"type": "state", "default": 0.0, "units": "1"}},
                "equations": [
                    {
                        "lhs": {"op": "D", "args": ["x"], "wrt": "t"},
                        "rhs": 0.0,
                    },
                ],
            },
        },
    }
    out = discretize(esm)
    lhs = out["models"]["M"]["equations"][0]["lhs"]
    # LHS must still be the derivative form; the rule only fires on RHS.
    assert isinstance(lhs, dict)
    assert lhs["op"] == "D"
