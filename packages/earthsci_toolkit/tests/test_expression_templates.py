"""Tests for parse-time expansion of `expression_templates` (RFC v2 §4, esm-giy)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from earthsci_toolkit.esm_types import ExprNode
from earthsci_toolkit.parse import SchemaValidationError, load


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "tests" / "valid" / "expression_templates_arrhenius.esm"


def _arrhenius_inline(a_pre: float, ea: float) -> ExprNode:
    return ExprNode(
        op="*",
        args=[
            a_pre,
            ExprNode(
                op="exp",
                args=[ExprNode(op="/", args=[ExprNode(op="-", args=[ea]), "T"])],
            ),
            "num_density",
        ],
    )


def test_fixture_loads_with_expanded_rates():
    esm = load(str(FIXTURE))
    rs = esm.reaction_systems["ToyArrhenius"]
    # `expression_templates` block is consumed at load: not exposed on the parsed object.
    assert not hasattr(rs, "expression_templates") or getattr(rs, "expression_templates", None) in (None, {})
    cases = [
        ("R1", 1.8e-12, 1500),
        ("R2", 3.0e-13, 460),
        ("R3", 4.5e-14, 920),
    ]
    by_id = {r.id: r for r in rs.reactions}
    for rid, a_pre, ea in cases:
        rate = by_id[rid].rate_constant
        assert rate == _arrhenius_inline(a_pre, ea), f"{rid} rate mismatch: {rate}"


def test_inline_dict_load_expands():
    data = json.loads(FIXTURE.read_text())
    esm = load(data)
    rs = esm.reaction_systems["ToyArrhenius"]
    assert rs.reactions[0].rate_constant == _arrhenius_inline(1.8e-12, 1500)


def test_pre_0_4_rejects_apply_expression_template():
    data = json.loads(FIXTURE.read_text())
    data["esm"] = "0.3.0"
    with pytest.raises(SchemaValidationError):
        load(data)


def test_unknown_template_rejected():
    data = json.loads(FIXTURE.read_text())
    data["reaction_systems"]["ToyArrhenius"]["reactions"][0]["rate"] = {
        "op": "apply_expression_template",
        "args": [],
        "name": "no_such_template",
        "bindings": {"A_pre": 1.0, "Ea": 1.0},
    }
    with pytest.raises(SchemaValidationError):
        load(data)


def test_missing_binding_rejected():
    data = json.loads(FIXTURE.read_text())
    data["reaction_systems"]["ToyArrhenius"]["reactions"][0]["rate"] = {
        "op": "apply_expression_template",
        "args": [],
        "name": "arrhenius",
        "bindings": {"A_pre": 1.0},
    }
    with pytest.raises(SchemaValidationError):
        load(data)


def test_extra_binding_rejected():
    data = json.loads(FIXTURE.read_text())
    data["reaction_systems"]["ToyArrhenius"]["reactions"][0]["rate"] = {
        "op": "apply_expression_template",
        "args": [],
        "name": "arrhenius",
        "bindings": {"A_pre": 1.0, "Ea": 1.0, "Junk": 2.0},
    }
    with pytest.raises(SchemaValidationError):
        load(data)


def test_expansion_is_deterministic():
    data = json.loads(FIXTURE.read_text())
    esm1 = load(json.loads(FIXTURE.read_text()))
    esm2 = load(json.loads(FIXTURE.read_text()))
    rs1 = esm1.reaction_systems["ToyArrhenius"]
    rs2 = esm2.reaction_systems["ToyArrhenius"]
    for r1, r2 in zip(rs1.reactions, rs2.reactions):
        assert r1.rate_constant == r2.rate_constant
