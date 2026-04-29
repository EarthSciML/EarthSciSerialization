"""Unit tests for expression_templates / apply_expression_template
(esm-spec §9.6, docs/rfcs/ast-expression-templates.md, esm-giy).
"""
from __future__ import annotations

import copy
import json

import pytest

from earthsci_toolkit.parse import load
from earthsci_toolkit.lower_expression_templates import (
    ExpressionTemplateError,
    lower_expression_templates,
    reject_expression_templates_pre_v04,
)


ARRHENIUS_FIXTURE: dict = {
    "esm": "0.4.0",
    "metadata": {"name": "expr_template_smoke", "authors": ["esm-giy"]},
    "reaction_systems": {
        "chem": {
            "species": {
                "A": {"default": 1.0},
                "B": {"default": 0.5},
                "C": {"default": 0.0},
            },
            "parameters": {
                "T": {"default": 298.15},
                "num_density": {"default": 2.5e19},
            },
            "expression_templates": {
                "arrhenius": {
                    "params": ["A_pre", "Ea"],
                    "body": {
                        "op": "*",
                        "args": [
                            "A_pre",
                            {
                                "op": "exp",
                                "args": [
                                    {
                                        "op": "/",
                                        "args": [
                                            {"op": "-", "args": ["Ea"]},
                                            "T",
                                        ],
                                    }
                                ],
                            },
                            "num_density",
                        ],
                    },
                }
            },
            "reactions": [
                {
                    "id": "R1",
                    "substrates": [{"species": "A", "stoichiometry": 1}],
                    "products": [{"species": "B", "stoichiometry": 1}],
                    "rate": {
                        "op": "apply_expression_template",
                        "args": [],
                        "name": "arrhenius",
                        "bindings": {"A_pre": 1.8e-12, "Ea": 1500},
                    },
                },
                {
                    "id": "R2",
                    "substrates": [{"species": "B", "stoichiometry": 1}],
                    "products": [{"species": "C", "stoichiometry": 1}],
                    "rate": {
                        "op": "apply_expression_template",
                        "args": [],
                        "name": "arrhenius",
                        "bindings": {"A_pre": 3.4e-13, "Ea": 800},
                    },
                },
            ],
        }
    },
}


def _inline_arrhenius(A: float, Ea: float) -> dict:
    return {
        "op": "*",
        "args": [
            A,
            {
                "op": "exp",
                "args": [
                    {"op": "/", "args": [{"op": "-", "args": [Ea]}, "T"]}
                ],
            },
            "num_density",
        ],
    }


def test_expansion_at_load_strips_templates_and_produces_inline_ast():
    expanded = lower_expression_templates(copy.deepcopy(ARRHENIUS_FIXTURE))
    chem = expanded["reaction_systems"]["chem"]
    assert "expression_templates" not in chem
    assert chem["reactions"][0]["rate"] == _inline_arrhenius(1.8e-12, 1500)
    assert chem["reactions"][1]["rate"] == _inline_arrhenius(3.4e-13, 800)


def test_lower_expression_templates_is_deterministic():
    a = lower_expression_templates(copy.deepcopy(ARRHENIUS_FIXTURE))
    b = lower_expression_templates(copy.deepcopy(ARRHENIUS_FIXTURE))
    assert a == b


def test_files_without_templates_pass_through_unchanged():
    fixture = {
        "esm": "0.4.0",
        "metadata": {"name": "no_templates", "authors": ["t"]},
        "reaction_systems": {
            "chem": {
                "species": {"A": {}},
                "parameters": {"k": {"default": 1.0}},
                "reactions": [
                    {
                        "id": "R1",
                        "substrates": [{"species": "A", "stoichiometry": 1}],
                        "products": None,
                        "rate": "k",
                    }
                ],
            }
        },
    }
    out = lower_expression_templates(copy.deepcopy(fixture))
    # Same shape as input, no expression_templates block introduced.
    assert "expression_templates" not in out["reaction_systems"]["chem"]
    assert out["reaction_systems"]["chem"]["reactions"][0]["rate"] == "k"


def test_rejects_apply_expression_template_pre_v04():
    fixture = copy.deepcopy(ARRHENIUS_FIXTURE)
    fixture["esm"] = "0.3.5"
    with pytest.raises(ExpressionTemplateError) as excinfo:
        reject_expression_templates_pre_v04(fixture)
    assert excinfo.value.code == "apply_expression_template_version_too_old"


def test_rejects_unknown_template_name():
    fixture = copy.deepcopy(ARRHENIUS_FIXTURE)
    fixture["reaction_systems"]["chem"]["reactions"][0]["rate"]["name"] = "missing"
    with pytest.raises(ExpressionTemplateError) as excinfo:
        lower_expression_templates(fixture)
    assert excinfo.value.code == "apply_expression_template_unknown_template"


def test_rejects_bindings_missing_a_param():
    fixture = copy.deepcopy(ARRHENIUS_FIXTURE)
    del fixture["reaction_systems"]["chem"]["reactions"][0]["rate"]["bindings"]["Ea"]
    with pytest.raises(ExpressionTemplateError) as excinfo:
        lower_expression_templates(fixture)
    assert excinfo.value.code == "apply_expression_template_bindings_mismatch"


def test_rejects_extra_bindings_param():
    fixture = copy.deepcopy(ARRHENIUS_FIXTURE)
    fixture["reaction_systems"]["chem"]["reactions"][0]["rate"]["bindings"]["bogus"] = 99
    with pytest.raises(ExpressionTemplateError) as excinfo:
        lower_expression_templates(fixture)
    assert excinfo.value.code == "apply_expression_template_bindings_mismatch"


def test_rejects_nested_apply_in_template_body():
    fixture = copy.deepcopy(ARRHENIUS_FIXTURE)
    fixture["reaction_systems"]["chem"]["expression_templates"]["arrhenius"]["body"] = {
        "op": "apply_expression_template",
        "args": [],
        "name": "arrhenius",
        "bindings": {"A_pre": 1, "Ea": 1},
    }
    with pytest.raises(ExpressionTemplateError) as excinfo:
        lower_expression_templates(fixture)
    assert excinfo.value.code == "apply_expression_template_recursive_body"


def test_ast_valued_bindings_are_substituted():
    fixture = copy.deepcopy(ARRHENIUS_FIXTURE)
    fixture["reaction_systems"]["chem"]["reactions"][0]["rate"]["bindings"]["Ea"] = {
        "op": "*",
        "args": [3, "T"],
    }
    out = lower_expression_templates(fixture)
    rate = out["reaction_systems"]["chem"]["reactions"][0]["rate"]
    assert rate["op"] == "*"
    # The exp's argument (-Ea/T) should now contain the (3*T) sub-AST.
    exp_node = rate["args"][1]
    assert exp_node["op"] == "exp"
    div_node = exp_node["args"][0]
    assert div_node["op"] == "/"
    neg_node = div_node["args"][0]
    assert neg_node["op"] == "-"
    inner = neg_node["args"][0]
    assert isinstance(inner, dict)
    assert inner["op"] == "*"


def test_conformance_fixture_matches_expanded_form():
    """Loading the conformance fixture must yield the canonical expanded form
    pinned in `tests/conformance/expression_templates/arrhenius_smoke/expanded.esm`.
    """
    import os

    here = os.path.dirname(__file__)
    # tests/test_expression_templates.py → packages/earthsci_toolkit/tests
    # → packages/earthsci_toolkit → packages → repo root.
    root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    fixture_path = os.path.join(
        root,
        "tests",
        "conformance",
        "expression_templates",
        "arrhenius_smoke",
        "fixture.esm",
    )
    expanded_path = os.path.join(
        root,
        "tests",
        "conformance",
        "expression_templates",
        "arrhenius_smoke",
        "expanded.esm",
    )
    with open(fixture_path) as fp:
        fixture_src = fp.read()
    with open(expanded_path) as fp:
        expanded_dict = json.load(fp)
    expanded_via_pass = lower_expression_templates(json.loads(fixture_src))
    assert (
        expanded_via_pass["reaction_systems"]["chem"]["reactions"]
        == expanded_dict["reaction_systems"]["chem"]["reactions"]
    )


def test_load_end_to_end_produces_inline_rate_in_typed_object():
    """The full ``load`` path should expand templates and surface inline ASTs."""
    file = load(json.dumps(ARRHENIUS_FIXTURE))
    rs = file.reaction_systems["chem"]
    rate = rs.reactions[0].rate_constant  # python binding stores rate as `rate_constant`
    # Walk the typed expression: should be `*` with three args, no apply op.
    assert rate.op == "*"

    def assert_no_apply(node):
        if hasattr(node, "op"):
            assert node.op != "apply_expression_template"
            for a in getattr(node, "args", []) or []:
                assert_no_apply(a)

    assert_no_apply(rate)
