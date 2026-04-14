"""Runtime loader for ``kind=grid`` DataLoaders.

Opens a gridded source file via xarray (falling back to netCDF4 for raw
netCDF), applies variable name remapping + unit conversion, and optionally
regrids onto a target lat/lon grid.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union

from ..esm_types import DataLoader, DataLoaderKind
from .mirror import open_with_fallback
from .regrid import regrid_latlon_to_target
from .time_resolution import file_anchor_for_time
from .url_template import expand_with_mirrors
from .variables import apply_variable_mapping


class GridLoaderError(RuntimeError):
    """Raised when grid data cannot be loaded."""


@dataclass
class GridLoadResult:
    """Result of a single ``GridLoader.load`` call.

    ``dataset`` is the raw (pre-remap) xarray.Dataset; ``variables`` maps
    schema-side variable names to unit-converted DataArrays (or raw arrays if
    xarray is unavailable).
    """

    urls_tried: List[str]
    dataset: Any
    variables: Dict[str, Any]


class GridLoader:
    """Materialise a ``kind=grid`` DataLoader at a given time."""

    def __init__(self, data_loader: DataLoader) -> None:
        if data_loader.kind != DataLoaderKind.GRID:
            raise GridLoaderError(
                f"GridLoader requires kind=grid; got {data_loader.kind}"
            )
        self.dl = data_loader

    def _resolve_urls(
        self,
        *,
        time: Optional[Union[_dt.datetime, _dt.date, str]],
        substitutions: Mapping[str, Any],
    ) -> List[str]:
        anchor: Optional[_dt.datetime]
        if time is not None and self.dl.temporal and self.dl.temporal.file_period:
            anchor = file_anchor_for_time(
                time,
                file_period=self.dl.temporal.file_period,
                start=self.dl.temporal.start,
            )
        elif isinstance(time, (_dt.datetime, _dt.date)):
            anchor = (
                time
                if isinstance(time, _dt.datetime)
                else _dt.datetime(time.year, time.month, time.day)
            )
        else:
            anchor = None
        return expand_with_mirrors(
            self.dl.source.url_template,
            self.dl.source.mirrors,
            date=anchor,
            variables=dict(substitutions),
        )

    def load(
        self,
        *,
        time: Optional[Union[_dt.datetime, _dt.date, str]] = None,
        target_grid: Optional[Mapping[str, Sequence[float]]] = None,
        opener: Optional[Any] = None,
        **substitutions: Any,
    ) -> GridLoadResult:
        """Open and decode a grid file.

        Parameters
        ----------
        time:
            Target timestamp used to expand ``{date:...}`` placeholders. Snapped
            to the file_period anchor when ``temporal`` is set.
        target_grid:
            Optional ``{"lon": [...], "lat": [...]}`` destination grid. Only
            valid when ``spatial.grid_type == "latlon"``.
        opener:
            Callable ``(url) -> xarray.Dataset``. Defaults to
            ``xarray.open_dataset``.
        **substitutions:
            Extra url template kwargs (``var``, ``species``, ``sector``, etc.).
        """
        urls = self._resolve_urls(time=time, substitutions=substitutions)
        if opener is None:
            opener = _default_xarray_opener()
        ds = open_with_fallback(urls, opener)
        raw_vars = _ds_to_mapping(ds)
        remapped = apply_variable_mapping(
            raw_vars, self.dl.variables, strict=True
        )
        if target_grid is not None:
            remapped = self._regrid_all(remapped, ds, target_grid)
        return GridLoadResult(urls_tried=urls, dataset=ds, variables=remapped)

    def _regrid_all(
        self,
        variables: Dict[str, Any],
        ds: Any,
        target_grid: Mapping[str, Sequence[float]],
    ) -> Dict[str, Any]:
        spatial = self.dl.spatial
        if spatial is None or spatial.grid_type != "latlon":
            raise GridLoaderError(
                "target_grid regridding is only supported for grid_type='latlon'"
            )
        src_lon = _lookup_coord(ds, ("lon", "longitude", "x"))
        src_lat = _lookup_coord(ds, ("lat", "latitude", "y"))
        tgt_lon = target_grid.get("lon")
        tgt_lat = target_grid.get("lat")
        if tgt_lon is None or tgt_lat is None:
            raise GridLoaderError(
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


def load_grid(
    data_loader: DataLoader,
    *,
    time: Optional[Union[_dt.datetime, _dt.date, str]] = None,
    target_grid: Optional[Mapping[str, Sequence[float]]] = None,
    opener: Optional[Any] = None,
    **substitutions: Any,
) -> GridLoadResult:
    """Convenience wrapper: instantiate a GridLoader and call ``load``."""
    return GridLoader(data_loader).load(
        time=time,
        target_grid=target_grid,
        opener=opener,
        **substitutions,
    )


def _default_xarray_opener():
    try:
        import xarray as xr
    except ImportError as exc:
        raise GridLoaderError(
            "grid loader default opener requires xarray; install xarray "
            "or pass an explicit `opener`"
        ) from exc

    def _open(url: str):
        return xr.open_dataset(url)

    return _open


def _ds_to_mapping(ds: Any) -> Mapping[str, Any]:
    if hasattr(ds, "data_vars"):
        return {name: ds[name] for name in ds.data_vars}
    if isinstance(ds, Mapping):
        return ds
    raise GridLoaderError(
        f"opener must return an xarray.Dataset or mapping; got {type(ds).__name__}"
    )


def _lookup_coord(ds: Any, candidates: Iterable[str]):
    if hasattr(ds, "coords"):
        for name in candidates:
            if name in ds.coords:
                return _as_array(ds.coords[name])
    if isinstance(ds, Mapping):
        for name in candidates:
            if name in ds:
                return _as_array(ds[name])
    raise GridLoaderError(
        f"source does not expose any of the expected coord names: {list(candidates)}"
    )


def _as_array(values: Any):
    if hasattr(values, "values"):
        return values.values
    return values
