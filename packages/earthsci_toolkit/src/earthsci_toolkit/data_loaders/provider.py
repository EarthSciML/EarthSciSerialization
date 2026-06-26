"""The cadence-aware **Provider** the loader-consumer driver builds and queries.

This is the ESS-side realisation of the EarthSciIO **Provider** contract
(earthsciio bead ``esio-9nb.3``): a per-loader object that ``simulate()``'s
segmented driver constructs **once at setup** and queries at cadence
boundaries —

* :meth:`Provider.materialize` — CONST loader, read once;
* :meth:`Provider.refresh` — DISCRETE loader, snap a time to the cadence anchor
  and return that record's native arrays;
* :meth:`Provider.refresh_times` — the cadence anchors over the run window, i.e.
  the solver tstops.

ESS does **not** import EarthSciIO (the rigs are decoupled — cross-repo
dependencies are tracked in beads, not in code). Instead the consumer accepts
any object conforming to the :class:`Provider` protocol. The in-tree
:class:`LoadDataProvider` — backed by :func:`data_loaders.runtime.load_data` —
is the default, and a real EarthSciIO ``Provider`` (whose
``materialize`` / ``refresh`` / ``refresh_times`` signatures match this protocol
exactly, per the ``esio-9nb.3`` gate) can be dropped in via
``simulate(..., provider_factory=...)`` with no change to ESS code.

The provider returns **raw native-grid data**; variable-name remap and regrid
stay in ESS (the C4 driver runs in the consumer, between the provider's native
output and the RHS registry — see :func:`simulation._provider_array`). For the
in-tree provider that native dataset is a
:class:`~earthsci_toolkit.data_loaders.grid.GridLoadResult`; for a real
EarthSciIO provider it is a ``NativeDataset``. The consumer bridges either
shape, so this module never needs the EarthSciIO container types.
"""

from __future__ import annotations

import datetime as _dt
import math
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Tuple

try:  # Protocol is stdlib from 3.8; guard keeps the import defensive.
    from typing import Protocol, runtime_checkable
except ImportError:  # pragma: no cover - 3.7 fallback
    Protocol = object  # type: ignore[assignment]

    def runtime_checkable(cls):  # type: ignore[misc]
        return cls

if TYPE_CHECKING:  # avoid a runtime import cycle with flatten/simulation.
    from ..flatten import LoaderField

#: A run window ``(start, end)`` of absolute datetimes bounding
#: :meth:`Provider.refresh_times` (and priming a DISCRETE :meth:`materialize`).
Window = Tuple[_dt.datetime, _dt.datetime]


@runtime_checkable
class Provider(Protocol):
    """Structural type for a loader-bound, cadence-aware data source.

    Matches the EarthSciIO ``Provider`` (``esio-9nb.3``) method surface the
    consumer relies on. ``materialize`` / ``refresh`` return a *native dataset*
    (a ``GridLoadResult`` from the in-tree provider, or a ``NativeDataset`` from
    a real EarthSciIO provider); :func:`simulation._provider_array` extracts the
    requested variable from either shape.
    """

    def materialize(self) -> Any:
        """Read a CONST loader's data once and return it."""

    def refresh(self, t: _dt.datetime) -> Any:
        """Return the native arrays for the cadence anchor at time ``t``."""

    def refresh_times(self) -> List[_dt.datetime]:
        """The cadence anchors (absolute datetimes) over the run window."""


#: A factory the consumer calls once per loader field at setup to build its
#: provider, given the field and its absolute run window (``None`` for CONST).
ProviderFactory = Callable[["LoaderField", Optional[Window]], Provider]


class LoadDataProvider:
    """In-tree default :class:`Provider` backed by ``runtime.load_data``.

    Conforms to the EarthSciIO ``Provider`` contract so the same consumer code
    path serves both the in-tree loaders and an injected EarthSciIO provider.
    Holds no decoded buffer of its own — ``load_data`` is the I/O — but exposes
    :meth:`refresh_times` computed from the loader's ``temporal`` cadence so the
    segmented driver's boundaries come from the provider, not local frequency
    arithmetic in the driver.
    """

    def __init__(self, field: "LoaderField", window: Optional[Window] = None) -> None:
        self.field = field
        self.window = window

    @property
    def _temporal(self) -> Any:
        return self.field.loader.temporal

    def _epoch(self) -> Optional[_dt.datetime]:
        """Absolute instant of simulation-clock 0 for this loader, or ``None``.

        Mirrors C1's clock mapping (``temporal.start`` is sim-clock zero), so a
        ``refresh_times`` anchor converts back to sim-clock by subtracting it.
        """
        temporal = self._temporal
        start = getattr(temporal, "start", None) if temporal is not None else None
        if not start:
            return None
        from .time_resolution import _coerce_datetime

        return _coerce_datetime(start)

    @property
    def is_const(self) -> bool:
        return self._temporal is None

    def materialize(self) -> Any:
        """CONST: read the single file once (sim time is irrelevant)."""
        from .runtime import load_data

        return load_data(self.field.loader, time=None)

    def refresh(self, t: Optional[_dt.datetime]) -> Any:
        """Load the file covering absolute time ``t`` (``None`` ⇒ unanchored)."""
        from .runtime import load_data

        return load_data(self.field.loader, time=t)

    def refresh_times(self) -> List[_dt.datetime]:
        """Cadence anchors in the run window — the solver tstops.

        Empty for a CONST loader, or when the window/epoch/frequency cannot be
        resolved (the consumer then falls back to local frequency arithmetic).
        Anchors are aligned to the loader epoch (``temporal.start``) and lie in
        ``[max(window.start, epoch), window.end)``, matching the EarthSciIO
        ``Provider.refresh_times`` semantics.
        """
        temporal = self._temporal
        freq = getattr(temporal, "frequency", None) if temporal is not None else None
        epoch = self._epoch()
        if not freq or epoch is None or self.window is None:
            return []
        from .time_resolution import TimeResolutionError, parse_iso_duration

        try:
            step = parse_iso_duration(freq).approximate_seconds()
        except TimeResolutionError:
            return []
        if step <= 0:
            return []
        delta = _dt.timedelta(seconds=step)
        lower = max(self.window[0], epoch)
        upper = self.window[1]
        # First aligned anchor at or after ``lower`` (ceil of the elapsed steps).
        elapsed = (lower - epoch).total_seconds()
        k = max(0, math.ceil(elapsed / step))
        anchor = epoch + k * delta
        out: List[_dt.datetime] = []
        while anchor < upper:
            out.append(anchor)
            anchor = anchor + delta
        return out


def build_default_provider(
    field: "LoaderField", window: Optional[Window] = None
) -> Provider:
    """Default :data:`ProviderFactory`: the in-tree :class:`LoadDataProvider`."""
    return LoadDataProvider(field, window)
