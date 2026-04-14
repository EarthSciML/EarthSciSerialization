"""Target-grid regridding with ``fill_value`` / ``extrapolation`` semantics.

This is a minimal bilinear regridder for ``latlon`` grids — enough to honour
the schema's ``DataLoaderRegridding`` settings without pulling in a heavy
dependency like xesmf. Callers that need higher-order regridders should do
that out-of-band and bypass this helper.

Supported extrapolation modes (from :class:`DataLoaderRegridding`):

- ``"clamp"`` — hold edge values (bilinear clipped to source extent)
- ``"nan"`` — set out-of-domain samples to ``fill_value`` (or NaN)
- ``"periodic"`` — wrap the longitude axis modulo 360°
"""

from __future__ import annotations

from typing import Any, Optional, Sequence


class RegriddingError(ValueError):
    """Raised when regridding cannot proceed."""


def _require_numpy():
    try:
        import numpy as _np

        return _np
    except ImportError as exc:
        raise RegriddingError(
            "regridding requires numpy; install numpy to use this helper"
        ) from exc


def regrid_latlon_to_target(
    values: Any,
    source_lon: Sequence[float],
    source_lat: Sequence[float],
    target_lon: Sequence[float],
    target_lat: Sequence[float],
    *,
    extrapolation: Optional[str] = None,
    fill_value: Optional[float] = None,
):
    """Bilinearly interpolate ``values`` from source to target lat/lon.

    ``values`` has shape ``(..., n_lat, n_lon)`` (lat is the second-to-last
    axis). Returns an array with shape ``(..., len(target_lat), len(target_lon))``.
    """
    np = _require_numpy()
    vals = np.asarray(values, dtype=float)
    src_lon = np.asarray(source_lon, dtype=float)
    src_lat = np.asarray(source_lat, dtype=float)
    tgt_lon = np.asarray(target_lon, dtype=float)
    tgt_lat = np.asarray(target_lat, dtype=float)
    if vals.ndim < 2:
        raise RegriddingError(
            f"values must have shape (..., nlat, nlon); got ndim={vals.ndim}"
        )
    if vals.shape[-1] != src_lon.size or vals.shape[-2] != src_lat.size:
        raise RegriddingError(
            f"values trailing shape {vals.shape[-2:]} does not match "
            f"source grid ({src_lat.size}, {src_lon.size})"
        )

    mode = (extrapolation or "clamp").lower()
    if mode not in ("clamp", "nan", "periodic"):
        raise RegriddingError(f"unknown extrapolation mode {extrapolation!r}")
    fill = float("nan") if fill_value is None else float(fill_value)

    lon_query = tgt_lon.copy()
    lat_query = tgt_lat.copy()
    if mode == "periodic":
        lon_min = float(src_lon[0])
        lon_max = float(src_lon[-1])
        span = lon_max - lon_min
        if span <= 0:
            raise RegriddingError("periodic regridding needs ascending source lon")
        lon_query = ((lon_query - lon_min) % span) + lon_min

    lon_idx = np.searchsorted(src_lon, lon_query) - 1
    lat_idx = np.searchsorted(src_lat, lat_query) - 1

    lon_oob = (lon_query < src_lon[0]) | (lon_query > src_lon[-1])
    lat_oob = (lat_query < src_lat[0]) | (lat_query > src_lat[-1])

    lon_idx = np.clip(lon_idx, 0, src_lon.size - 2)
    lat_idx = np.clip(lat_idx, 0, src_lat.size - 2)

    x0 = src_lon[lon_idx]
    x1 = src_lon[lon_idx + 1]
    y0 = src_lat[lat_idx]
    y1 = src_lat[lat_idx + 1]
    dx = np.where(x1 != x0, (lon_query - x0) / (x1 - x0), 0.0)
    dy = np.where(y1 != y0, (lat_query - y0) / (y1 - y0), 0.0)
    if mode == "clamp":
        dx = np.clip(dx, 0.0, 1.0)
        dy = np.clip(dy, 0.0, 1.0)

    lat_grid, lon_grid = np.meshgrid(np.arange(tgt_lat.size), np.arange(tgt_lon.size), indexing="ij")
    li = lat_idx[lat_grid]
    xi = lon_idx[lon_grid]
    fy = dy[lat_grid]
    fx = dx[lon_grid]

    v00 = vals[..., li, xi]
    v01 = vals[..., li, xi + 1]
    v10 = vals[..., li + 1, xi]
    v11 = vals[..., li + 1, xi + 1]

    top = v00 * (1 - fx) + v01 * fx
    bot = v10 * (1 - fx) + v11 * fx
    out = top * (1 - fy) + bot * fy

    if mode == "nan":
        oob_mask = lon_oob[lon_grid] | lat_oob[lat_grid]
        out = np.where(oob_mask, fill, out)
    elif mode == "clamp":
        pass
    return out
