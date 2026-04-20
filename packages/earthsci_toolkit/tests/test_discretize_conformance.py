"""Manifest-driven conformance harness for the discretize() pipeline.

Mirrors ``packages/EarthSciSerialization.jl/test/conformance_discretize_test.jl``.
Each fixture is parsed, passed through :func:`discretize` with the
manifest's default options, emitted as canonical JSON (sorted keys, no
whitespace, RFC §5.4.6 number format, matching Julia's reference
emitter), and compared byte-for-byte against the committed golden.

See ``tests/conformance/discretize/README.md`` for the full contract.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Any, Mapping

import pytest

from earthsci_toolkit import discretize
from earthsci_toolkit.canonicalize import format_canonical_float


_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONF_DIR = _REPO_ROOT / "tests" / "conformance" / "discretize"
_MANIFEST = _CONF_DIR / "manifest.json"
_UPDATE_GOLDEN = os.environ.get("UPDATE_DISCRETIZE_GOLDEN", "") == "1"


def _parse_float_maybe_int(s: str):
    """Mirror JSON3's behavior of coercing whole-number floats to ints.

    Julia's discretize pipeline reads fixtures with JSON3, which promotes
    whole-number floats (``1.0``) to ``Int64``. For byte-identical
    golden parity, Python parses the same way.
    """
    f = float(s)
    if f.is_integer() and abs(f) < (1 << 53):
        return int(f)
    return f


def _load_input(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh, parse_float=_parse_float_maybe_int)


def _emit_string(s: str) -> str:
    out = ['"']
    for ch in s:
        cu = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif cu == 0x08:
            out.append("\\b")
        elif cu == 0x09:
            out.append("\\t")
        elif cu == 0x0A:
            out.append("\\n")
        elif cu == 0x0C:
            out.append("\\f")
        elif cu == 0x0D:
            out.append("\\r")
        elif cu < 0x20:
            out.append(f"\\u{cu:04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _emit(x: Any, buf: io.StringIO) -> None:
    if x is None:
        buf.write("null")
    elif isinstance(x, bool):
        buf.write("true" if x else "false")
    elif isinstance(x, int):
        buf.write(str(x))
    elif isinstance(x, float):
        buf.write(format_canonical_float(x))
    elif isinstance(x, str):
        buf.write(_emit_string(x))
    elif isinstance(x, Mapping):
        buf.write("{")
        keys = sorted(str(k) for k in x.keys())
        for i, k in enumerate(keys):
            if i > 0:
                buf.write(",")
            buf.write(_emit_string(k))
            buf.write(":")
            _emit(x[k], buf)
        buf.write("}")
    elif isinstance(x, (list, tuple)):
        buf.write("[")
        for i, v in enumerate(x):
            if i > 0:
                buf.write(",")
            _emit(v, buf)
        buf.write("]")
    else:
        raise TypeError(f"cannot canonically emit value of type {type(x).__name__}")


def _canonical_json(doc: Any) -> str:
    buf = io.StringIO()
    _emit(doc, buf)
    return buf.getvalue()


def _load_manifest() -> Mapping[str, Any]:
    with open(_MANIFEST, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _fixture_cases():
    manifest = _load_manifest()
    opts = manifest.get("options", {})
    cases = []
    for fixture in manifest.get("fixtures", []):
        cases.append(
            pytest.param(
                str(fixture["id"]),
                _CONF_DIR / str(fixture["input"]),
                _CONF_DIR / str(fixture["golden"]),
                dict(opts),
                id=str(fixture["id"]),
            )
        )
    return cases


@pytest.mark.parametrize("fid,input_path,golden_path,opts", _fixture_cases())
def test_conformance_discretize(fid, input_path, golden_path, opts):
    assert input_path.is_file(), f"input missing: {input_path}"

    raw = _load_input(input_path)
    kwargs = {
        "max_passes": int(opts.get("max_passes", 32)),
        "strict_unrewritten": bool(opts.get("strict_unrewritten", True)),
    }

    first_out = discretize(raw, **kwargs)
    first_bytes = _canonical_json(first_out)

    # Determinism: second call → identical bytes.
    second_raw = _load_input(input_path)
    second_out = discretize(second_raw, **kwargs)
    second_bytes = _canonical_json(second_out)
    assert first_bytes == second_bytes, f"{fid}: non-deterministic output"

    if _UPDATE_GOLDEN or not golden_path.is_file():
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        with open(golden_path, "w", encoding="utf-8") as fh:
            fh.write(first_bytes)
            fh.write("\n")
    else:
        with open(golden_path, "r", encoding="utf-8") as fh:
            golden = fh.read().rstrip("\n")
        assert first_bytes == golden, (
            f"{fid}: canonical JSON does not match golden\n"
            f"  got:    {first_bytes}\n"
            f"  wanted: {golden}"
        )
