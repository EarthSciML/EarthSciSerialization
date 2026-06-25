"""Load-time rejection of legacy (pre-0.7.0) pure-I/O data-loader shapes
(esm-spec.md §8 / RFC pure-io-data-loaders §4.1, bead ess-v9a.7).

In v0.7.0 the ``DataLoader`` is reduced to pure I/O: the loader-level
``regridding`` and ``spatial`` blocks were removed. Regridding/reprojection
are now per-variable ``Model.regrid`` concerns, and the native grid is a GDD
``Grid`` under ``grid``. A pre-0.7.0 loader file that still carries one of
those blocks is rejected at load with a named, version-keyed diagnostic,
mirroring :func:`reject_expression_templates_pre_v04`.
"""
from __future__ import annotations

import re
from typing import Any

DATA_LOADER_REGRIDDING_REMOVED = "data_loader_regridding_removed"
DATA_LOADER_SPATIAL_REMOVED = "data_loader_spatial_removed"


class LegacyDataLoaderError(Exception):
    """Raised when a loader carries a ``DataLoader`` block removed in v0.7.0.

    The ``code`` attribute carries one of the stable diagnostic codes:
    ``data_loader_regridding_removed``, ``data_loader_spatial_removed``.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code


def _is_object(v: Any) -> bool:
    return isinstance(v, dict)


def reject_legacy_data_loader_shapes(view: Any) -> None:
    """Reject ``data_loaders.<name>.regridding`` / ``.spatial`` blocks in files
    declaring ``esm`` < 0.7.0, with the named diagnostics
    ``data_loader_regridding_removed`` / ``data_loader_spatial_removed``.
    Mirrors the equivalent TS / Julia / Rust / Go checks for
    cross-binding-uniform diagnostics.
    """
    if not _is_object(view):
        return
    esm = view.get("esm")
    if not isinstance(esm, str):
        return
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", esm)
    if not m:
        return
    major, minor = int(m.group(1)), int(m.group(2))
    if not (major == 0 and minor < 7):
        return

    loaders = view.get("data_loaders")
    if not _is_object(loaders):
        return

    regridding_paths: list[str] = []
    spatial_paths: list[str] = []
    for lname, loader in loaders.items():
        if not _is_object(loader):
            continue
        if "regridding" in loader:
            regridding_paths.append(f"/data_loaders/{lname}/regridding")
        if "spatial" in loader:
            spatial_paths.append(f"/data_loaders/{lname}/spatial")

    if regridding_paths:
        raise LegacyDataLoaderError(
            DATA_LOADER_REGRIDDING_REMOVED,
            f"DataLoader `regridding` was removed in esm 0.7.0 (regridding is now "
            f"a per-variable model concern — see `Model.regrid`; RFC "
            f"pure-io-data-loaders §4.1); file declares {esm}. Migrate by deleting "
            f"the block and moving the per-variable regridding choice to the owning "
            f"model. Offending paths: {', '.join(regridding_paths)}",
        )
    if spatial_paths:
        raise LegacyDataLoaderError(
            DATA_LOADER_SPATIAL_REMOVED,
            f"DataLoader `spatial` was removed in esm 0.7.0 (the native grid is now "
            f"a GDD `Grid` under `grid`; RFC pure-io-data-loaders §4.1); file "
            f"declares {esm}. Migrate by replacing the block with a `grid` GDD Grid. "
            f"Offending paths: {', '.join(spatial_paths)}",
        )
