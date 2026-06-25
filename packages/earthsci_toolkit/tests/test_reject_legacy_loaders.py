"""Load-time rejection of legacy (pre-0.7.0) pure-I/O data-loader shapes
(esm-spec.md §8 / RFC pure-io-data-loaders §4.1, bead ess-v9a.7).

Exercises the cross-binding conformance fixtures in
``tests/conformance/migration/0_6_to_0_7/``.
"""
import json
from pathlib import Path

import pytest

from earthsci_toolkit import load
from earthsci_toolkit.reject_legacy_loaders import (
    LegacyDataLoaderError,
    reject_legacy_data_loader_shapes,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FIX_DIR = REPO_ROOT / "tests" / "conformance" / "migration" / "0_6_to_0_7"


def _text(name: str) -> str:
    return (FIX_DIR / name).read_text()


def test_rejects_removed_regridding_with_named_diagnostic():
    with pytest.raises(LegacyDataLoaderError) as exc:
        load(_text("loader_regridding_removed.esm"))
    assert exc.value.code == "data_loader_regridding_removed"


def test_rejects_removed_spatial_with_named_diagnostic():
    with pytest.raises(LegacyDataLoaderError) as exc:
        load(_text("loader_spatial_removed.esm"))
    assert exc.value.code == "data_loader_spatial_removed"


def test_accepts_migrated_0_7_0_loader():
    # The migrated 0.7.0 pure-I/O shape must load without error.
    esm_file = load(_text("loader_migrated.esm"))
    assert esm_file is not None


def test_version_gated_070_file_is_a_noop():
    # The check only fires for esm < 0.7.0; a 0.7.0 file is a no-op even with
    # a stray `regridding` key (schema validation owns that case).
    reject_legacy_data_loader_shapes(
        {"esm": "0.7.0", "data_loaders": {"w": {"regridding": {}}}}
    )


def test_no_data_loaders_block_is_a_noop():
    reject_legacy_data_loader_shapes({"esm": "0.6.0", "models": {}})


def test_direct_call_reports_offending_path():
    raw = json.loads(_text("loader_spatial_removed.esm"))
    with pytest.raises(LegacyDataLoaderError) as exc:
        reject_legacy_data_loader_shapes(raw)
    assert "/data_loaders/weather/spatial" in str(exc.value)
