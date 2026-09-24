"""A minimal light-curve container used throughout the pipeline.

We deliberately use a small dataclass of NumPy arrays instead of lightkurve's
``LightCurve`` object. It keeps the numerical code independent of lightkurve
internals, pickles cheaply into worker processes (injection-recovery runs
thousands of searches in parallel), and makes synthetic test data trivial.
Times are TESS Barycentric Julian Dates (BTJD = BJD - 2457000) in days.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .utils import bin_timeseries, to_jsonable


@dataclass
class LightCurve:
    """Time series of (normalised) flux with per-point uncertainties.

    Attributes
    ----------
    time : BTJD days, sorted ascending.
    flux : relative flux (median ~1 after normalisation).
    flux_err : 1-sigma uncertainty on ``flux``.
    sector : TESS sector of each point (optional).
    meta : free-form metadata (target identifiers, processing provenance, ...).
    """

    time: np.ndarray
    flux: np.ndarray
    flux_err: np.ndarray
    sector: np.ndarray | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.time = np.asarray(self.time, dtype=float)
        self.flux = np.asarray(self.flux, dtype=float)
        self.flux_err = np.asarray(self.flux_err, dtype=float)
        if self.sector is not None:
            self.sector = np.asarray(self.sector, dtype=int)
        n = self.time.size
        shapes = [self.flux.size, self.flux_err.size]
        if self.sector is not None:
            shapes.append(self.sector.size)
        if any(s != n for s in shapes):
            raise ValueError("time, flux, flux_err (and sector) must have the same length")
        if n > 1 and np.any(np.diff(self.time) < 0):
            order = np.argsort(self.time, kind="stable")
            self.time = self.time[order]
            self.flux = self.flux[order]
            self.flux_err = self.flux_err[order]
            if self.sector is not None:
                self.sector = self.sector[order]

    def __len__(self) -> int:
        return int(self.time.size)

    @property
    def baseline(self) -> float:
        """Time between the first and last sample (days)."""
        return float(self.time[-1] - self.time[0]) if len(self) > 1 else 0.0

    @property
    def cadence(self) -> float:
        """Median sampling interval (days)."""
        return float(np.median(np.diff(self.time))) if len(self) > 1 else float("nan")

    @property
    def sectors(self) -> list[int]:
        """Sorted list of distinct TESS sectors present."""
        if self.sector is None:
            return []
        return sorted({int(s) for s in np.unique(self.sector)})

    def select(self, mask: np.ndarray) -> LightCurve:
        """Return a new light curve containing only samples where ``mask`` is True."""
        mask = np.asarray(mask)
        return LightCurve(
            self.time[mask],
            self.flux[mask],
            self.flux_err[mask],
            None if self.sector is None else self.sector[mask],
            dict(self.meta),
        )

    def copy(self) -> LightCurve:
        return self.select(np.ones(len(self), dtype=bool))

    def with_flux(
        self, flux: np.ndarray, flux_err: np.ndarray | None = None, **meta: Any
    ) -> LightCurve:
        """Copy with replaced flux (and optionally errors); ``meta`` entries are merged in."""
        new_meta = dict(self.meta)
        new_meta.update(meta)
        return LightCurve(
            self.time.copy(),
            np.asarray(flux, dtype=float),
            self.flux_err.copy() if flux_err is None else np.asarray(flux_err, dtype=float),
            None if self.sector is None else self.sector.copy(),
            new_meta,
        )

    def finite(self) -> LightCurve:
        """Drop samples with non-finite time, flux, or uncertainty."""
        good = np.isfinite(self.time) & np.isfinite(self.flux) & np.isfinite(self.flux_err)
        return self.select(good)

    def bin(self, width: float, min_count: int = 1) -> LightCurve:
        """Inverse-variance weighted binning in time (``width`` in days).

        Bins are defined on a global grid, so no bin spans a data gap in any
        meaningful way: empty bins are simply dropped.
        """
        if width <= 0:
            return self.copy()
        t, f, e, _ = bin_timeseries(
            self.time, self.flux, self.flux_err, width=width, min_count=min_count
        )
        sector = None
        if self.sector is not None and t.size:
            # Assign each bin the sector of the nearest original sample.
            idx = np.clip(np.searchsorted(self.time, t), 0, len(self) - 1)
            sector = self.sector[idx]
        meta = dict(self.meta)
        meta["binned_width_days"] = width
        return LightCurve(t, f, e, sector, meta)

    # ------------------------------------------------------------------ I/O
    def save(self, path: str | Path) -> Path:
        """Save to a compressed ``.npz`` file (metadata stored as JSON)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        arrays = {"time": self.time, "flux": self.flux, "flux_err": self.flux_err}
        if self.sector is not None:
            arrays["sector"] = self.sector
        arrays["meta_json"] = np.array(json.dumps(to_jsonable(self.meta)))
        np.savez_compressed(path, **arrays)
        return path

    @classmethod
    def load(cls, path: str | Path) -> LightCurve:
        with np.load(Path(path), allow_pickle=False) as data:
            meta = json.loads(str(data["meta_json"])) if "meta_json" in data else {}
            sector = data["sector"] if "sector" in data else None
            return cls(data["time"], data["flux"], data["flux_err"], sector, meta)
