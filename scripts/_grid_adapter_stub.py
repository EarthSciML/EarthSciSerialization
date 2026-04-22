#!/usr/bin/env python3
"""
Internal stub adapter used by run-grid-conformance.py --self-test (gt-usme).

Not a binding implementation. Emits canned results so the runner's
plumbing — adapter dispatch, result diffing, exit codes — can be tested
without depending on Julia / Python / Rust / TS being built.

CLI mirrors the real adapter contract:
    --manifest <path>   read fixtures and queries
    --output <path>     write results JSON

Behavior is selected by --mode:
    agree        emit canonical canned values (used as the reference)
    disagree     emit values that diverge enough to fail tolerance
    unsupported  emit status=unsupported for every query
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# Canonical canned values. The runner self-test compares two stub instances
# to each other; "agree" returns these, "disagree" perturbs them.
CANON = {
    "to_esm_sha":  "deadbeef" * 8,           # 64-hex SHA-256 placeholder
    "cell_center": [0.5, 0.5, 0.5],
    "neighbors":   [1, 2, 3, 4],
    "metric_eval": 0.015625,
}


def fabricate(op: str, mode: str) -> dict:
    if mode == "unsupported":
        return {"status": "unsupported"}
    if op not in CANON:
        return {"status": "unsupported"}
    val = CANON[op]
    if mode == "disagree":
        if op == "to_esm_sha":
            val = "cafef00d" * 8
        elif op == "neighbors":
            val = [9, 8, 7, 6]
        elif op == "cell_center":
            val = [v + 1.0 for v in val]
        elif op == "metric_eval":
            val = val * 2.0
    return {"status": "ok", "result": val}


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--binding", required=True)
    p.add_argument("--mode", default="agree",
                   choices=["agree", "disagree", "unsupported"])
    args = p.parse_args(argv)

    with args.manifest.open() as f:
        manifest = json.load(f)

    fixtures_out: dict[str, dict] = {}
    for fx in manifest.get("fixtures", []):
        queries_out: dict[str, dict] = {}
        for q in fx.get("queries", []):
            queries_out[q["id"]] = fabricate(q["op"], args.mode)
        fixtures_out[fx["id"]] = {"status": "ok", "queries": queries_out}

    payload = {
        "binding":         args.binding,
        "binding_version": "stub-0.0.0",
        "fixtures":        fixtures_out,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
