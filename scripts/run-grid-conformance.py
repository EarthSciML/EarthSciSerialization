#!/usr/bin/env python3
"""
Family-agnostic cross-binding grid conformance runner (gt-usme).

Drives per-binding GridAccessor adapters against a manifest of fixtures
+ query points and reports pass/fail. Family-specific suites live in
EarthSciDiscretizations/conformance/grids/<family>/manifest.json; this
runner is the consumer of those manifests.

See tests/conformance/grids/README.md for the full contract.

Usage:
    python scripts/run-grid-conformance.py \\
        --manifest <path-to-manifest.json> \\
        --output  <path-to-results.json> \\
        [--bindings julia,python,rust,typescript] \\
        [--adapter-dir <dir-of-adapters>]

    python scripts/run-grid-conformance.py --self-test

Exit codes:
    0  every required binding passed every fixture
    1  one or more failures (or self-test failed)
    2  manifest / config error (no run attempted)

Environment variables:
    EARTHSCI_GRID_ADAPTER_<BINDING>    Override adapter command per binding.
                                       Tokenized with shlex.split.
    EARTHSCI_GRID_ADAPTER_DIR          Search path for adapters (in addition
                                       to PATH).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "tests" / "conformance" / "grids" / "manifest.schema.json"
EXAMPLE_DIR = REPO_ROOT / "tests" / "conformance" / "grids" / "example"
STUB_ADAPTER = REPO_ROOT / "scripts" / "_grid_adapter_stub.py"

KNOWN_BINDINGS = ("julia", "python", "rust", "typescript", "go")
DEFAULT_REL_TOL = 1e-14
DEFAULT_ABS_TOL = 0.0
DEFAULT_REFERENCE = "julia"


def _eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


# --- Manifest loading -----------------------------------------------------


class ManifestError(Exception):
    pass


def load_manifest(path: Path) -> dict:
    try:
        with path.open() as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ManifestError(f"failed to load manifest {path}: {e}") from e

    _validate_manifest_shape(manifest, path)
    return manifest


def _validate_manifest_shape(manifest: Any, path: Path) -> None:
    """Minimal structural validation. Full JSON Schema lives in
    manifest.schema.json; we re-check the load-bearing fields here so
    the runner can give a clean error without a schema-validator dep."""
    if not isinstance(manifest, dict):
        raise ManifestError(f"{path}: top-level must be a JSON object")
    if manifest.get("category") != "grid_conformance":
        raise ManifestError(
            f"{path}: category must be 'grid_conformance', got {manifest.get('category')!r}"
        )
    if not isinstance(manifest.get("version"), str):
        raise ManifestError(f"{path}: version must be a string")
    fixtures = manifest.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise ManifestError(f"{path}: fixtures must be a non-empty array")
    seen_ids: set[str] = set()
    for i, fx in enumerate(fixtures):
        if not isinstance(fx, dict):
            raise ManifestError(f"{path}: fixtures[{i}] must be an object")
        fid = fx.get("id")
        if not isinstance(fid, str) or not fid:
            raise ManifestError(f"{path}: fixtures[{i}].id must be a non-empty string")
        if fid in seen_ids:
            raise ManifestError(f"{path}: duplicate fixture id {fid!r}")
        seen_ids.add(fid)
        grid = fx.get("grid")
        if not isinstance(grid, dict) or "source" not in grid:
            raise ManifestError(
                f"{path}: fixtures[{fid}].grid must be an object with a 'source' field"
            )
        if grid["source"] not in ("generator", "file"):
            raise ManifestError(
                f"{path}: fixtures[{fid}].grid.source must be 'generator' or 'file'"
            )


# --- Adapter discovery / invocation --------------------------------------


def discover_adapter(binding: str, adapter_dir: Path | None) -> list[str] | None:
    """Return the argv prefix to invoke the adapter, or None if missing."""
    env_key = f"EARTHSCI_GRID_ADAPTER_{binding.upper()}"
    env_cmd = os.environ.get(env_key)
    if env_cmd:
        return shlex.split(env_cmd)

    name = f"earthsci-grid-adapter-{binding}"
    if adapter_dir:
        candidate = adapter_dir / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return [str(candidate)]
    on_path = shutil.which(name)
    if on_path:
        return [on_path]
    extra = os.environ.get("EARTHSCI_GRID_ADAPTER_DIR")
    if extra:
        candidate = Path(extra) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return [str(candidate)]
    return None


def run_adapter(
    binding: str,
    argv: list[str],
    manifest_path: Path,
    timeout: float | None = None,
) -> dict:
    with tempfile.NamedTemporaryFile(
        "r", suffix=".json", prefix=f"grid-conf-{binding}-", delete=False
    ) as tmp:
        out_path = Path(tmp.name)
    try:
        cmd = [*argv, "--manifest", str(manifest_path), "--output", str(out_path)]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as e:
            return {
                "binding": binding,
                "adapter_status": "missing",
                "error": str(e),
                "fixtures": {},
            }
        except subprocess.TimeoutExpired as e:
            return {
                "binding": binding,
                "adapter_status": "timeout",
                "error": f"adapter timed out after {timeout}s",
                "stderr": (e.stderr or "").strip()[-2000:],
                "fixtures": {},
            }

        if not out_path.exists() or out_path.stat().st_size == 0:
            return {
                "binding": binding,
                "adapter_status": "no_output",
                "error": "adapter did not write the output file",
                "exit_code": proc.returncode,
                "stdout": (proc.stdout or "").strip()[-2000:],
                "stderr": (proc.stderr or "").strip()[-2000:],
                "fixtures": {},
            }
        try:
            with out_path.open() as f:
                payload = json.load(f)
        except json.JSONDecodeError as e:
            return {
                "binding": binding,
                "adapter_status": "invalid_output",
                "error": f"adapter output is not valid JSON: {e}",
                "exit_code": proc.returncode,
                "stderr": (proc.stderr or "").strip()[-2000:],
                "fixtures": {},
            }

        if not isinstance(payload, dict) or "fixtures" not in payload:
            return {
                "binding": binding,
                "adapter_status": "invalid_output",
                "error": "adapter output missing 'fixtures' field",
                "exit_code": proc.returncode,
                "fixtures": {},
            }

        # Stamp adapter_status; preserve adapter-reported binding name if any.
        payload.setdefault("binding", binding)
        payload["adapter_status"] = "ok"
        payload["exit_code"] = proc.returncode
        return payload
    finally:
        try:
            out_path.unlink()
        except OSError:
            pass


# --- Result comparison ----------------------------------------------------


def _resolve_tol(
    suite_tol: dict, fixture_tol: dict, query_tol: dict, field: str | None
) -> tuple[float, float]:
    rel = DEFAULT_REL_TOL
    abs_ = DEFAULT_ABS_TOL
    for src in (suite_tol, fixture_tol):
        if not src:
            continue
        rel = src.get("default_rel", rel)
        abs_ = src.get("default_abs", abs_)
        per_field = src.get("per_field") or {}
        if field is not None and field in per_field:
            rel = per_field[field]
    if query_tol:
        rel = query_tol.get("rel", rel)
        abs_ = query_tol.get("abs", abs_)
    return rel, abs_


def _compare_numbers(a: float, b: float, rel: float, abs_: float) -> tuple[bool, float]:
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b, 0.0 if a == b else math.inf
    af, bf = float(a), float(b)
    if math.isnan(af) and math.isnan(bf):
        return True, 0.0
    if math.isnan(af) or math.isnan(bf):
        return False, math.inf
    diff = abs(af - bf)
    if math.isinf(af) or math.isinf(bf):
        return af == bf, 0.0 if af == bf else math.inf
    if diff <= abs_:
        return True, diff
    denom = max(abs(af), abs(bf))
    if denom == 0.0:
        return diff == 0.0, diff
    rel_diff = diff / denom
    return rel_diff <= rel, rel_diff


def _is_int_like(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def compare_results(
    op: str, ref: Any, other: Any, rel: float, abs_: float
) -> dict:
    """Compare adapter results for one query, return diff record."""
    if op == "to_esm_sha":
        ok = isinstance(ref, str) and isinstance(other, str) and ref == other
        return {"match": ok, "kind": "sha"} if ok else {
            "match": False, "kind": "sha", "ref": ref, "other": other,
        }
    if op == "neighbors":
        ok = ref == other
        return {"match": ok, "kind": "int_array"} if ok else {
            "match": False, "kind": "int_array", "ref": ref, "other": other,
        }
    # cell_center, metric_eval, and any future float-valued op
    return _compare_numeric(ref, other, rel, abs_)


def _compare_numeric(ref: Any, other: Any, rel: float, abs_: float) -> dict:
    if isinstance(ref, list) and isinstance(other, list):
        if len(ref) != len(other):
            return {
                "match": False, "kind": "shape_mismatch",
                "ref_len": len(ref), "other_len": len(other),
            }
        worst = 0.0
        worst_idx: list[int] = []
        for i, (a, b) in enumerate(zip(ref, other)):
            sub = _compare_numeric(a, b, rel, abs_)
            if not sub["match"]:
                return {
                    "match": False, "kind": "elem_mismatch",
                    "index": [i, *sub.get("index", [])],
                    "ref": sub.get("ref", a), "other": sub.get("other", b),
                    "rel_diff": sub.get("rel_diff"),
                }
            if sub.get("rel_diff", 0.0) > worst:
                worst = sub["rel_diff"]
                worst_idx = [i, *sub.get("worst_index", [])]
        return {"match": True, "kind": "float_array",
                "worst_rel_diff": worst, "worst_index": worst_idx}
    if isinstance(ref, (int, float)) and isinstance(other, (int, float)):
        if _is_int_like(ref) and _is_int_like(other):
            ok = ref == other
            return {"match": ok, "kind": "int"} if ok else {
                "match": False, "kind": "int", "ref": ref, "other": other,
            }
        ok, diff = _compare_numbers(ref, other, rel, abs_)
        if ok:
            return {"match": True, "kind": "float", "rel_diff": diff}
        return {"match": False, "kind": "float",
                "ref": ref, "other": other, "rel_diff": diff,
                "tol_rel": rel, "tol_abs": abs_}
    # Fall-through for unexpected shapes (objects, mixed, etc.) — exact eq.
    ok = ref == other
    return {"match": ok, "kind": "structural"} if ok else {
        "match": False, "kind": "structural", "ref": ref, "other": other,
    }


# --- Aggregation ----------------------------------------------------------


def aggregate(
    manifest: dict,
    adapter_results: dict[str, dict],
    reference: str,
) -> dict:
    suite_tol = manifest.get("tolerances") or {}
    fixtures = manifest["fixtures"]
    bindings = list(adapter_results.keys())
    required = set(manifest.get("bindings_required") or [])

    fixtures_report: dict[str, Any] = {}
    binding_status: dict[str, str] = {b: "ok" for b in bindings}

    for fx in fixtures:
        fid = fx["id"]
        fx_tol = fx.get("tolerances") or {}
        sha_check = fx.get("sha_check", True)

        # Resolve per-binding payload for this fixture.
        per_binding = {}
        for b in bindings:
            ar = adapter_results[b]
            if ar.get("adapter_status") != "ok":
                per_binding[b] = {"status": "adapter_unavailable",
                                  "reason": ar.get("adapter_status"),
                                  "error": ar.get("error")}
                continue
            fxres = ar.get("fixtures", {}).get(fid)
            if fxres is None:
                per_binding[b] = {"status": "missing",
                                  "error": "adapter did not report this fixture"}
                continue
            per_binding[b] = fxres

        # Choose the reference payload: prefer the configured reference
        # binding; fall back to the first binding with status==ok.
        ref_binding: str | None = None
        if reference in per_binding and per_binding[reference].get("status") == "ok":
            ref_binding = reference
        else:
            for b in bindings:
                if per_binding[b].get("status") == "ok":
                    ref_binding = b
                    break

        # Per-query diff against the reference.
        queries_report: dict[str, Any] = {}
        for q in fx.get("queries") or []:
            qid = q["id"]
            op = q["op"]
            q_tol = q.get("tolerance") or {}
            field = q["args"][0] if op == "metric_eval" and q.get("args") else None
            rel, abs_ = _resolve_tol(suite_tol, fx_tol, q_tol, field)

            ref_val = None
            ref_status = "no_reference"
            if ref_binding is not None:
                rq = per_binding[ref_binding].get("queries", {}).get(qid)
                if rq is not None:
                    ref_status = rq.get("status", "unknown")
                    ref_val = rq.get("result")

            per_b: dict[str, Any] = {}
            for b in bindings:
                if per_binding[b].get("status") != "ok":
                    per_b[b] = {"status": "skipped",
                                "reason": per_binding[b].get("status")}
                    continue
                qres = per_binding[b].get("queries", {}).get(qid)
                if qres is None:
                    per_b[b] = {"status": "missing"}
                    continue
                qstatus = qres.get("status", "unknown")
                if qstatus != "ok":
                    per_b[b] = {"status": qstatus,
                                "error": qres.get("error")}
                    continue
                if b == ref_binding:
                    per_b[b] = {"status": "ok", "is_reference": True,
                                "result": qres.get("result")}
                    continue
                if ref_status != "ok":
                    per_b[b] = {"status": "ok_no_reference",
                                "result": qres.get("result")}
                    continue
                diff = compare_results(op, ref_val, qres.get("result"), rel, abs_)
                rec = {"status": "ok" if diff["match"] else "mismatch",
                       "diff": diff}
                per_b[b] = rec

            # Bindings supporting this query (status==ok or mismatch).
            supported = [b for b, r in per_b.items()
                         if r.get("status") in ("ok", "mismatch", "ok_no_reference")]
            if not supported:
                queries_report[qid] = {"status": "all_unsupported",
                                       "op": op, "bindings": per_b}
                continue
            mismatched = [b for b, r in per_b.items()
                          if r.get("status") == "mismatch"]
            queries_report[qid] = {
                "status": "mismatch" if mismatched else "ok",
                "op": op,
                "ref_binding": ref_binding,
                "tol_rel": rel,
                "tol_abs": abs_,
                "bindings": per_b,
            }
            for b in mismatched:
                binding_status[b] = "fail"

        # SHA check is implemented as a synthetic query; honor sha_check flag
        # only by suppressing failure attribution if disabled.
        if not sha_check:
            for qid, qr in queries_report.items():
                if qr["op"] == "to_esm_sha" and qr["status"] == "mismatch":
                    qr["status"] = "ok_sha_check_disabled"
                    qr["note"] = "fixture has sha_check: false"

        fx_status = "ok"
        for qr in queries_report.values():
            if qr["status"] == "mismatch":
                fx_status = "fail"
                break

        # If the fixture itself failed at adapter level for ANY binding,
        # mark binding as fail (independent of query mismatches).
        for b, payload in per_binding.items():
            if payload.get("status") == "error":
                binding_status[b] = "fail"

        fixtures_report[fid] = {
            "status": fx_status,
            "ref_binding": ref_binding,
            "per_binding": {b: {"status": p.get("status"),
                                "error": p.get("error")}
                            for b, p in per_binding.items()},
            "queries": queries_report,
        }

    overall = "ok"
    for b in required:
        if b not in adapter_results or adapter_results[b].get("adapter_status") != "ok":
            binding_status[b] = "missing"
            overall = "fail"
        elif binding_status.get(b) == "fail":
            overall = "fail"

    return {
        "status": overall,
        "manifest_family": manifest.get("family"),
        "manifest_version": manifest["version"],
        "reference_binding": reference,
        "bindings_required": sorted(required),
        "bindings_optional": sorted(manifest.get("bindings_optional") or []),
        "binding_status": binding_status,
        "fixtures": fixtures_report,
    }


# --- Driver ---------------------------------------------------------------


def run_suite(
    manifest_path: Path,
    bindings: list[str],
    adapter_dir: Path | None,
    output_path: Path,
    reference: str,
    timeout: float | None,
) -> int:
    manifest = load_manifest(manifest_path)

    if not bindings:
        bindings = list(manifest.get("bindings_required") or [])
        bindings.extend(b for b in (manifest.get("bindings_optional") or [])
                        if b not in bindings)
    if not bindings:
        _eprint("error: no bindings to run (manifest declares none and "
                "--bindings was empty)")
        return 2
    for b in bindings:
        if b not in KNOWN_BINDINGS:
            _eprint(f"error: unknown binding {b!r}; known: {KNOWN_BINDINGS}")
            return 2

    started = _dt.datetime.now(_dt.timezone.utc).isoformat()
    adapter_results: dict[str, dict] = {}
    for b in bindings:
        argv = discover_adapter(b, adapter_dir)
        if argv is None:
            adapter_results[b] = {
                "binding": b,
                "adapter_status": "missing",
                "error": ("adapter not found; expected on PATH as "
                          f"earthsci-grid-adapter-{b}, in --adapter-dir, "
                          f"or via $EARTHSCI_GRID_ADAPTER_{b.upper()}"),
                "fixtures": {},
            }
            continue
        adapter_results[b] = run_adapter(b, argv, manifest_path, timeout)

    report = aggregate(manifest, adapter_results, reference)
    report["started_at"] = started
    report["finished_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
    report["manifest_path"] = str(manifest_path)
    report["adapters"] = {b: {"status": r.get("adapter_status"),
                              "error": r.get("error")}
                          for b, r in adapter_results.items()}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")

    _print_summary(report)
    return 0 if report["status"] == "ok" else 1


def _print_summary(report: dict) -> None:
    print(f"=== Grid Conformance Report ===")
    print(f"manifest:  {report['manifest_path']}")
    print(f"family:    {report.get('manifest_family') or '(unspecified)'}")
    print(f"reference: {report['reference_binding']}")
    print(f"status:    {report['status'].upper()}")
    print()
    print("Per-binding status:")
    for b, s in report["binding_status"].items():
        print(f"  {b:>12}  {s}")
    print()
    fail_count = sum(1 for f in report["fixtures"].values()
                     if f["status"] != "ok")
    print(f"Fixtures: {len(report['fixtures'])} total, {fail_count} failing")
    for fid, fx in report["fixtures"].items():
        if fx["status"] == "ok":
            continue
        print(f"  FAIL {fid}")
        for qid, qr in fx["queries"].items():
            if qr["status"] != "mismatch":
                continue
            print(f"    query {qid} (op={qr['op']}): mismatch vs "
                  f"{qr['ref_binding']}")
            for b, br in qr["bindings"].items():
                if br.get("status") == "mismatch":
                    print(f"      {b}: {br.get('diff')}")


# --- Self-test ------------------------------------------------------------


def self_test(adapter_dir: Path | None) -> int:
    """Drive the runner against the in-tree example using the stub adapter.

    Validates: manifest loading, adapter dispatch via env-var override,
    diff classification (ok / mismatch / unsupported), and exit codes.
    """
    if not EXAMPLE_DIR.is_dir():
        _eprint(f"self-test: example dir missing: {EXAMPLE_DIR}")
        return 1
    if not STUB_ADAPTER.is_file():
        _eprint(f"self-test: stub adapter missing: {STUB_ADAPTER}")
        return 1

    manifest_path = EXAMPLE_DIR / "manifest.json"
    if not manifest_path.is_file():
        _eprint(f"self-test: example manifest missing: {manifest_path}")
        return 1

    rc = 0
    with tempfile.TemporaryDirectory(prefix="grid-conf-selftest-") as tmpd:
        tmp = Path(tmpd)

        # Scenario A: two bindings agree -> exit 0.
        env_ok = os.environ.copy()
        for b in ("julia", "rust"):
            env_ok[f"EARTHSCI_GRID_ADAPTER_{b.upper()}"] = (
                f"{sys.executable} {STUB_ADAPTER} --binding {b} --mode agree"
            )
        out_a = tmp / "agree.json"
        proc_a = subprocess.run(
            [sys.executable, str(Path(__file__)),
             "--manifest", str(manifest_path),
             "--bindings", "julia,rust",
             "--output", str(out_a)],
            env=env_ok, capture_output=True, text=True,
        )
        if proc_a.returncode != 0:
            _eprint("self-test FAIL [agree]: expected exit 0, got",
                    proc_a.returncode)
            _eprint(proc_a.stdout, proc_a.stderr)
            rc = 1
        else:
            with out_a.open() as f:
                rep = json.load(f)
            if rep["status"] != "ok":
                _eprint("self-test FAIL [agree]: report status != ok")
                rc = 1

        # Scenario B: rust disagrees -> exit 1, mismatch reported.
        env_bad = os.environ.copy()
        env_bad["EARTHSCI_GRID_ADAPTER_JULIA"] = (
            f"{sys.executable} {STUB_ADAPTER} --binding julia --mode agree"
        )
        env_bad["EARTHSCI_GRID_ADAPTER_RUST"] = (
            f"{sys.executable} {STUB_ADAPTER} --binding rust --mode disagree"
        )
        out_b = tmp / "disagree.json"
        proc_b = subprocess.run(
            [sys.executable, str(Path(__file__)),
             "--manifest", str(manifest_path),
             "--bindings", "julia,rust",
             "--output", str(out_b)],
            env=env_bad, capture_output=True, text=True,
        )
        if proc_b.returncode != 1:
            _eprint("self-test FAIL [disagree]: expected exit 1, got",
                    proc_b.returncode)
            _eprint(proc_b.stdout, proc_b.stderr)
            rc = 1
        else:
            with out_b.open() as f:
                rep = json.load(f)
            if rep["status"] != "fail":
                _eprint("self-test FAIL [disagree]: status != fail")
                rc = 1
            elif rep["binding_status"].get("rust") != "fail":
                _eprint("self-test FAIL [disagree]: rust not marked fail")
                rc = 1

        # Scenario C: missing required adapter -> exit 1.
        env_miss = {k: v for k, v in os.environ.items()
                    if not k.startswith("EARTHSCI_GRID_ADAPTER_")}
        env_miss["PATH"] = "/nonexistent"
        env_miss["EARTHSCI_GRID_ADAPTER_DIR"] = "/nonexistent"
        out_c = tmp / "missing.json"
        proc_c = subprocess.run(
            [sys.executable, str(Path(__file__)),
             "--manifest", str(manifest_path),
             "--bindings", "julia,rust",
             "--output", str(out_c)],
            env=env_miss, capture_output=True, text=True,
        )
        if proc_c.returncode != 1:
            _eprint("self-test FAIL [missing]: expected exit 1, got",
                    proc_c.returncode)
            _eprint(proc_c.stdout, proc_c.stderr)
            rc = 1

        # Scenario D: unsupported op surfaces correctly.
        env_unsup = os.environ.copy()
        env_unsup["EARTHSCI_GRID_ADAPTER_JULIA"] = (
            f"{sys.executable} {STUB_ADAPTER} --binding julia --mode unsupported"
        )
        env_unsup["EARTHSCI_GRID_ADAPTER_RUST"] = (
            f"{sys.executable} {STUB_ADAPTER} --binding rust --mode unsupported"
        )
        out_d = tmp / "unsup.json"
        proc_d = subprocess.run(
            [sys.executable, str(Path(__file__)),
             "--manifest", str(manifest_path),
             "--bindings", "julia,rust",
             "--output", str(out_d)],
            env=env_unsup, capture_output=True, text=True,
        )
        if proc_d.returncode != 0:
            _eprint("self-test FAIL [unsupported]: expected exit 0, got",
                    proc_d.returncode)
            _eprint(proc_d.stdout, proc_d.stderr)
            rc = 1

    if rc == 0:
        print("self-test: OK")
    else:
        print("self-test: FAILED")
    return rc


# --- CLI ------------------------------------------------------------------


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--manifest", type=Path,
                   help="Path to the family-specific manifest.json.")
    p.add_argument("--output", type=Path,
                   default=Path("conformance-results/grids/report.json"),
                   help="Where to write the aggregated report.")
    p.add_argument("--bindings", default="",
                   help="Comma-separated list of bindings to run "
                        "(default: union of manifest's required + optional).")
    p.add_argument("--adapter-dir", type=Path, default=None,
                   help="Directory to search for adapter binaries "
                        "(in addition to PATH and per-binding env vars).")
    p.add_argument("--reference", default=DEFAULT_REFERENCE,
                   choices=KNOWN_BINDINGS,
                   help="Reference binding for ULP ties (default: julia).")
    p.add_argument("--timeout", type=float, default=None,
                   help="Per-adapter timeout in seconds.")
    p.add_argument("--self-test", action="store_true",
                   help="Run the runner's built-in self-test against the "
                        "in-tree stub adapter and example manifest, then exit.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.self_test:
        return self_test(args.adapter_dir)

    if not args.manifest:
        _eprint("error: --manifest is required (or use --self-test)")
        return 2
    if not args.manifest.is_file():
        _eprint(f"error: manifest not found: {args.manifest}")
        return 2

    bindings = [b.strip() for b in args.bindings.split(",") if b.strip()]

    try:
        return run_suite(
            manifest_path=args.manifest,
            bindings=bindings,
            adapter_dir=args.adapter_dir,
            output_path=args.output,
            reference=args.reference,
            timeout=args.timeout,
        )
    except ManifestError as e:
        _eprint(f"manifest error: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
