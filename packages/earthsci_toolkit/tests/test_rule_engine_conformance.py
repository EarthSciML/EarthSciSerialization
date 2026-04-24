"""Cross-binding rule-engine fixture consumer.

Reads ``tests/conformance/discretization/infra/rule_engine/*.json`` and
asserts that ``canonical_json(rewrite(parse(input), parse(rules), ctx))``
equals each fixture's ``expect.canonical_json`` byte-for-byte (for
``kind: output`` fixtures) or that the engine aborts with the expected
error code (for ``kind: error`` fixtures). Same fixture set consumed by
every binding — passing here means this binding matches the cross-binding
rule-engine contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from earthsci_toolkit.canonicalize import canonical_json
from earthsci_toolkit.esm_types import ExprNode
from earthsci_toolkit.rule_engine import (
    RuleContext,
    RuleEngineError,
    parse_rules,
    rewrite,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = (
    REPO_ROOT / "tests" / "conformance" / "discretization" / "infra" / "rule_engine"
)


def _wire_to_expr(node):
    """Convert a JSON-deserialized fixture into an ESM expression tree."""
    if isinstance(node, dict) and "op" in node and "args" in node:
        kwargs = {k: v for k, v in node.items() if k not in ("op", "args")}
        return ExprNode(
            op=node["op"],
            args=[_wire_to_expr(a) for a in node["args"]],
            **kwargs,
        )
    if isinstance(node, list):
        return [_wire_to_expr(a) for a in node]
    return node


def _load_manifest():
    path = FIXTURES_DIR / "manifest.json"
    with path.open() as fh:
        return json.load(fh)


def _build_ctx(raw):
    if raw is None:
        return RuleContext()
    return RuleContext(
        grids=dict(raw.get("grids", {})),
        variables=dict(raw.get("variables", {})),
    )


@pytest.mark.parametrize(
    "fixture_id", [f["id"] for f in _load_manifest()["fixtures"]]
)
def test_rule_engine_conformance(fixture_id):
    fixture_meta = next(
        f for f in _load_manifest()["fixtures"] if f["id"] == fixture_id
    )
    with (FIXTURES_DIR / fixture_meta["path"]).open() as fh:
        fixture = json.load(fh)

    rules = parse_rules(fixture["rules"])
    expr = _wire_to_expr(fixture["input"])
    ctx = _build_ctx(fixture.get("context"))
    max_passes = fixture.get("max_passes", 32)

    # RFC §5.2.7 fixtures require a per-query-point scope evaluator. The
    # Python binding is a parse-only consumer for these (see manifest note);
    # `parse_rules` above already asserted the fixture loads, so skip the
    # evaluation assertion.
    if fixture.get("requires_per_point_scope"):
        pytest.skip(
            "fixture requires RFC §5.2.7 per-query-point scope evaluator "
            "(Python binding is parse-only for this capability)"
        )

    expect = fixture["expect"]
    if expect["kind"] == "output":
        rewritten = rewrite(expr, rules, ctx, max_passes=max_passes)
        got = canonical_json(rewritten)
        assert got == expect["canonical_json"], (
            f"\n  id: {fixture_id}\n  got:  {got}\n  want: {expect['canonical_json']}"
        )
    elif expect["kind"] == "error":
        with pytest.raises(RuleEngineError) as excinfo:
            rewrite(expr, rules, ctx, max_passes=max_passes)
        assert excinfo.value.code == expect["code"], (
            f"\n  id: {fixture_id}\n  got code:  {excinfo.value.code}"
            f"\n  want code: {expect['code']}"
        )
    else:
        pytest.fail(f"unknown expect.kind: {expect['kind']}")
