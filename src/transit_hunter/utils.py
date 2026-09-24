"""Small numerical helpers shared across the pipeline."""

from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from astropy import constants as _const
from scipy.ndimage import median_filter

# Physical constants in SI units, taken from astropy so that every module uses
# the same (IAU 2015 nominal / CODATA) values.
G = _const.G.value
R_SUN = _const.R_sun.value
M_SUN = _const.M_sun.value
R_EARTH = _const.R_earth.value
R_JUP = _const.R_jup.value
AU = _const.au.value
DAY = 86400.0
#: Mean solar density in kg m^-3 (~1410). Stellar densities are quoted in these units.
RHO_SUN = M_SUN / (4.0 / 3.0 * math.pi * R_SUN**3)


def robust_std(x: np.ndarray) -> float:
    """Gaussian-equivalent standard deviation from the median absolute deviation.

    1.4826 * MAD equals sigma for normally distributed data but is insensitive to
    the transits, flares, and outliers that inflate a plain standard deviation.
    """
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan")
    return float(1.4826 * np.median(np.abs(x - np.median(x))))


def fold(time: np.ndarray, period: float, t0: float) -> np.ndarray:
    """Time since the nearest mid-transit, in the units of ``time``, in [-P/2, P/2)."""
    return (np.asarray(time, dtype=float) - t0 + 0.5 * period) % period - 0.5 * period


def transit_mask(time: np.ndarray, period: float, t0: float, duration: float) -> np.ndarray:
    """Boolean mask that is True within ``duration / 2`` of any mid-transit time."""
    return np.abs(fold(time, period, t0)) < 0.5 * duration


def epoch_index(time: np.ndarray, period: float, t0: float) -> np.ndarray:
    """Integer transit epoch (cycle number) of the transit nearest to each time."""
    return np.round((np.asarray(time, dtype=float) - t0) / period).astype(int)


def segment_bounds(time: np.ndarray, max_gap: float) -> list[tuple[int, int]]:
    """Split a sorted time array into contiguous segments.

    Returns ``(start, stop)`` index pairs (``stop`` exclusive) such that no two
    consecutive samples inside a segment are separated by more than ``max_gap``.
    """
    time = np.asarray(time, dtype=float)
    if time.size == 0:
        return []
    breaks = np.flatnonzero(np.diff(time) > max_gap) + 1
    starts = np.concatenate([[0], breaks])
    stops = np.concatenate([breaks, [time.size]])
    return list(zip(starts.tolist(), stops.tolist(), strict=True))


def running_median(
    time: np.ndarray, values: np.ndarray, window: float, max_gap: float | None = None
) -> np.ndarray:
    """Running median with a window of ``window`` (time units), evaluated per segment.

    The filter operates in cadence space inside each contiguous segment (TESS
    2-min data are uniformly sampled apart from gaps), which lets us use the fast
    C implementation in :func:`scipy.ndimage.median_filter`. Segments are split at
    gaps larger than ``max_gap`` (default: half the window) so the median never
    mixes data from either side of a data gap.
    """
    time = np.asarray(time, dtype=float)
    values = np.asarray(values, dtype=float)
    out = np.full_like(values, np.nan)
    if max_gap is None:
        max_gap = 0.5 * window
    for start, stop in segment_bounds(time, max_gap):
        seg_t = time[start:stop]
        seg_v = values[start:stop]
        if seg_t.size == 1:
            out[start:stop] = seg_v
            continue
        cadence = np.median(np.diff(seg_t))
        size = max(3, round(window / cadence))
        size += 1 - size % 2  # odd window so the filter is centred
        out[start:stop] = median_filter(seg_v, size=size, mode="nearest")
    return out


def bin_timeseries(
    x: np.ndarray,
    y: np.ndarray,
    yerr: np.ndarray | None = None,
    width: float | None = None,
    edges: np.ndarray | None = None,
    min_count: int = 1,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Bin ``y(x)`` into bins of fixed ``width`` (or explicit ``edges``).

    Returns ``(x_mean, y_mean, y_err, count)`` for every bin with at least
    ``min_count`` samples. With ``yerr`` the mean is inverse-variance weighted
    and its uncertainty is ``1/sqrt(sum(w))``; without it, the uncertainty is the
    standard error of the mean (NaN for single-sample bins).
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    good = np.isfinite(x) & np.isfinite(y)
    if yerr is not None:
        yerr = np.asarray(yerr, dtype=float)
        good &= np.isfinite(yerr) & (yerr > 0)
    x, y = x[good], y[good]
    if yerr is not None:
        yerr = yerr[good]
    empty = (np.array([]),) * 4
    if x.size == 0:
        return empty

    if edges is None:
        if width is None or width <= 0:
            raise ValueError("either a positive `width` or `edges` must be given")
        idx = np.floor((x - x.min()) / width).astype(np.int64)
    else:
        edges = np.asarray(edges, dtype=float)
        idx = np.searchsorted(edges, x, side="right") - 1
        inside = (idx >= 0) & (idx < edges.size - 1)
        x, y, idx = x[inside], y[inside], idx[inside]
        if yerr is not None:
            yerr = yerr[inside]
        if x.size == 0:
            return empty

    _, inverse = np.unique(idx, return_inverse=True)
    count = np.bincount(inverse).astype(float)
    x_mean = np.bincount(inverse, weights=x) / count
    if yerr is not None:
        w = 1.0 / yerr**2
        wsum = np.bincount(inverse, weights=w)
        y_mean = np.bincount(inverse, weights=w * y) / wsum
        y_err = 1.0 / np.sqrt(wsum)
    else:
        y_mean = np.bincount(inverse, weights=y) / count
        # Sum of squared deviations (numerically safer than E[y^2] - E[y]^2 for y ~ 1).
        ss = np.bincount(inverse, weights=(y - y_mean[inverse]) ** 2)
        var = ss / np.maximum(count - 1.0, 1.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            y_err = np.where(count > 1, np.sqrt(var / count), np.nan)
    keep = count >= min_count
    return x_mean[keep], y_mean[keep], y_err[keep], count[keep]


def binned_rms(
    time: np.ndarray, flux: np.ndarray, width: float, min_fraction: float = 0.5
) -> float:
    """Scatter of the flux after averaging in bins of length ``width``.

    For white noise this equals ``sigma / sqrt(n_per_bin)``; correlated ("red")
    noise makes it larger. Using this quantity at the transit-duration timescale
    gives a transit S/N that is honest about stellar and instrumental red noise
    (Pont, Zucker & Queloz 2006). Bins with fewer than ``min_fraction`` of the
    expected number of samples (e.g. at gap edges) are ignored, and a robust
    scatter estimate is used so that stray residual events do not dominate.
    """
    time = np.asarray(time, dtype=float)
    flux = np.asarray(flux, dtype=float)
    good = np.isfinite(time) & np.isfinite(flux)
    time, flux = time[good], flux[good]
    if time.size < 3:
        return float("nan")
    cadence = np.median(np.diff(np.sort(time)))
    expected = max(width / cadence, 1.0)
    _, means, _, counts = bin_timeseries(time, flux, width=width)
    means = means[counts >= min_fraction * expected]
    if means.size < 3:
        return float("nan")
    return robust_std(means)


def log_uniform(
    rng: np.random.Generator, low: float, high: float, size: int | None = None
) -> np.ndarray | float:
    """Draw from a distribution uniform in ``log(x)`` between ``low`` and ``high``."""
    return np.exp(rng.uniform(np.log(low), np.log(high), size=size))


def to_jsonable(obj: Any) -> Any:
    """Recursively convert NumPy types, dataclasses, and paths to JSON-safe objects.

    Non-finite floats become ``None`` so that the output is strict JSON.
    """
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return to_jsonable(dataclasses.asdict(obj))
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple | set):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [to_jsonable(v) for v in obj.tolist()]
    if isinstance(obj, np.generic):
        return to_jsonable(obj.item())
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, Path):
        return str(obj)
    return obj


def write_json(path: str | Path, obj: Any) -> Path:
    """Write ``obj`` as indented, strict JSON (creating parent folders)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(obj), indent=2, allow_nan=False) + "\n")
    return path
