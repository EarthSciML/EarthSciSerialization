"""Runtime data loaders for the STAC-like DataLoader schema.

Dispatches on DataLoader.kind (grid/points/static) and implements URL template
expansion, mirror fallback, time->file resolution, variable remapping with
unit conversion, and regridding onto target grids.
"""

from .url_template import (
    UrlTemplateError,
    expand_url_template,
    expand_with_mirrors,
    template_placeholders,
)
from .time_resolution import (
    TimeResolutionError,
    parse_iso_duration,
    file_anchor_for_time,
    file_anchors_in_range,
    records_for_file,
)
from .mirror import (
    MirrorFallbackError,
    open_with_fallback,
)
from .variables import (
    UnitConversionError,
    apply_variable_mapping,
    apply_unit_conversion,
)
from .regrid import (
    RegriddingError,
    regrid_latlon_to_target,
)
from .grid import (
    GridLoaderError,
    GridLoader,
    load_grid,
)
from .points import (
    PointsLoaderError,
    PointsLoader,
    load_points,
)
from .static_loader import (
    StaticLoaderError,
    StaticLoader,
    load_static,
)
from .runtime import (
    DataLoaderDispatchError,
    load_data,
    resolve_files,
)

__all__ = [
    "UrlTemplateError",
    "expand_url_template",
    "expand_with_mirrors",
    "template_placeholders",
    "TimeResolutionError",
    "parse_iso_duration",
    "file_anchor_for_time",
    "file_anchors_in_range",
    "records_for_file",
    "MirrorFallbackError",
    "open_with_fallback",
    "UnitConversionError",
    "apply_variable_mapping",
    "apply_unit_conversion",
    "RegriddingError",
    "regrid_latlon_to_target",
    "GridLoaderError",
    "GridLoader",
    "load_grid",
    "PointsLoaderError",
    "PointsLoader",
    "load_points",
    "StaticLoaderError",
    "StaticLoader",
    "load_static",
    "DataLoaderDispatchError",
    "load_data",
    "resolve_files",
]
