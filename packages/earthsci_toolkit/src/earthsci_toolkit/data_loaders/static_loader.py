"""Runtime loader for ``kind=static`` DataLoaders.

Static loaders describe time-invariant sources — elevation, fuel model codes,
etc. No ``{date}`` expansion is performed; the URL is opened as-is through the
configured opener. Variable remapping and unit conversion still apply.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ..esm_types import DataLoader, DataLoaderKind
from .grid import GridLoaderError, _default_xarray_opener, _ds_to_mapping, _lookup_coord, _as_array
from .mirror import open_with_fallback
from .regrid import regrid_latlon_to_target
from .url_template import expand_with_mirrors
from .variables import apply_variable_mapping


class StaticLoaderError(RuntimeError):
    """Raised when a static source cannot be loaded."""


@dataclass
class StaticLoadResult:
    """Result of a single ``StaticLoader.load`` call."""

    urls_tried: List[str]
    dataset: Any
    variables: Dict[str, Any]


class StaticLoader:
    """Materialise a ``kind=static`` DataLoader."""

    def __init__(self, data_loader: DataLoader) -> None:
        if data_loader.kind != DataLoaderKind.STATIC:
            raise StaticLoaderError(
                f"StaticLoader requires kind=static; got {data_loader.kind}"
            )
        self.dl = data_loader

    def load(
        self,
        *,
        target_grid: Optional[Mapping[str, Sequence[float]]] = None,
        opener: Optional[Any] = None,
        **substitutions: Any,
    ) -> StaticLoadResult:
        urls = expand_with_mirrors(
            self.dl.source.url_template,
            self.dl.source.mirrors,
            date=None,
            variables=dict(substitutions),
        )
        if opener is None:
            opener = _default_xarray_opener()
        try:
            ds = open_with_fallback(urls, opener)
        except GridLoaderError as exc:
            raise StaticLoaderError(str(exc)) from exc
        raw = _ds_to_mapping(ds)
        remapped = apply_variable_mapping(raw, self.dl.variables, strict=True)
        if target_grid is not None:
            remapped = self._regrid(remapped, ds, target_grid)
        return StaticLoadResult(urls_tried=urls, dataset=ds, variables=remapped)

    def _regrid(
        self,
        variables: Dict[str, Any],
        ds: Any,
        target_grid: Mapping[str, Sequence[float]],
    ) -> Dict[str, Any]:
        spatial = self.dl.spatial
        if spatial is None or spatial.grid_type != "latlon":
            raise StaticLoaderError(
                "target_grid regridding is only supported for grid_type='latlon'"
            )
        src_lon = _lookup_coord(ds, ("lon", "longitude", "x"))
        src_lat = _lookup_coord(ds, ("lat", "latitude", "y"))
        tgt_lon = target_grid.get("lon")
        tgt_lat = target_grid.get("lat")
        if tgt_lon is None or tgt_lat is None:
            raise StaticLoaderError(
                "target_grid must contain 'lon' and 'lat' arrays"
            )
        regridding = self.dl.regridding
        extrap = regridding.extrapolation if regridding else None
        fill = regridding.fill_value if regridding else None
        out: Dict[str, Any] = {}
        for name, values in variables.items():
            arr = _as_array(values)
            out[name] = regrid_latlon_to_target(
                arr,
                source_lon=src_lon,
                source_lat=src_lat,
                target_lon=tgt_lon,
                target_lat=tgt_lat,
                extrapolation=extrap,
                fill_value=fill,
            )
        return out


def load_static(
    data_loader: DataLoader,
    *,
    target_grid: Optional[Mapping[str, Sequence[float]]] = None,
    opener: Optional[Any] = None,
    **substitutions: Any,
) -> StaticLoadResult:
    """Convenience wrapper: instantiate and call ``StaticLoader.load``."""
    return StaticLoader(data_loader).load(
        target_grid=target_grid, opener=opener, **substitutions
    )
