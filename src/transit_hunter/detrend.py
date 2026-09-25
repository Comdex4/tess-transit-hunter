"""Remove stellar variability with a robust, time-windowed filter.

The default detrender is Tukey's biweight location estimator evaluated in a
sliding time window (implemented in ``wotan``). In the benchmark of Hippke et
al. (2019, AJ 158, 143) this robust slider was the best-performing method for
transit searches: it follows rotational modulation and slow instrumental drifts
while being nearly blind to a transit, because the in-transit points are
down-weighted as outliers of the window's flux distribution.

Choosing the window is a trade-off. A transit of duration T loses depth when
the window is not much longer than T (the filter starts to "eat" the dip);
too long a window fails to follow fast variability. A window of about three
times the longest transit duration of interest preserves the depth well (see
:func:`recommended_window`). Where transit times are already known, masking
them (``mask=...``) removes the residual bias altogether: masked points are
excluded from every window's location estimate, and the trend underneath a
transit is determined only by the out-of-transit neighbours.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .lightcurve import LightCurve
from .plotting import BLUE, INK_MUTED, ORANGE, new_figure, save_figure, style
from .utils import bin_timeseries, robust_std, segment_bounds, transit_mask

#: wotan methods that are time-windowed sliders (and therefore support masking).
TIME_WINDOWED_METHODS = frozenset(
    {
        "biweight",
        "median",
        "mean",
        "welsch",
        "andrewsinewave",
        "hodges",
        "trim_mean",
        "winsorize",
        "hampelfilt",
        "huber_psi",
        "tau",
    }
)


@dataclass(frozen=True)
class DetrendConfig:
    """Detrending settings.

    Attributes
    ----------
    method : a wotan time-windowed slider (default Tukey biweight).
    window_length : full window width in days.
    break_tolerance : gaps longer than this (days) split the light curve into
        segments that are detrended independently.
    edge_cutoff : days removed at the start and end of every segment, where
        the window is one-sided and the trend is less reliable.
    cval : tuning constant of the robust estimator in units of the MAD
        (``None`` = wotan default, 5 for the biweight).
    """

    method: str = "biweight"
    window_length: float = 0.75
    break_tolerance: float = 0.5
    edge_cutoff: float = 0.0
    cval: float | None = None


@dataclass
class DetrendResult:
    """Output of :func:`detrend`. All arrays are aligned with ``flat.time``."""

    flat: LightCurve
    trend: np.ndarray
    raw: LightCurve
    mask: np.ndarray | None
    config: DetrendConfig


def recommended_window(duration: float, factor: float = 3.0) -> float:
    """Window length (days) that preserves a transit of ``duration`` days.

    Hippke et al. (2019) recommend ~3x the transit duration for the biweight.
    """
    return factor * duration


def _ephemeris_tuple(item: Any) -> tuple[float, float, float]:
    if hasattr(item, "period"):
        return float(item.period), float(item.t0), float(item.duration)
    period, t0, duration = item
    return float(period), float(t0), float(duration)


def ephemeris_mask(
    time: np.ndarray, ephemerides: Iterable[Any], width_factor: float = 1.5
) -> np.ndarray:
    """Union of in-transit masks for several ephemerides.

    Each ephemeris is ``(period, t0, duration)`` (days) or any object with
    ``period``, ``t0``, and ``duration`` attributes. The masked window is
    ``width_factor * duration`` wide, centred on each mid-transit time, so that
    ingress/egress and small ephemeris errors are safely covered.
    """
    time = np.asarray(time, dtype=float)
    mask = np.zeros(time.size, dtype=bool)
    for item in ephemerides:
        period, t0, duration = _ephemeris_tuple(item)
        mask |= transit_mask(time, period, t0, width_factor * duration)
    return mask


def _fill_trend(time: np.ndarray, trend: np.ndarray, max_gap: float) -> np.ndarray:
    """Linearly interpolate undefined trend values inside each data segment.

    The trend can be undefined where an entire window is masked (a long transit
    and a short window) or at trimmed edges; interpolating from the nearest
    defined values inside the same segment is the natural continuation.
    """
    trend = trend.copy()
    for start, stop in segment_bounds(time, max_gap):
        seg = trend[start:stop]
        ok = np.isfinite(seg) & (seg > 0)
        if ok.all() or not ok.any():
            continue
        t = time[start:stop]
        seg[~ok] = np.interp(t[~ok], t[ok], seg[ok])
        trend[start:stop] = seg
    return trend


def detrend(
    lc: LightCurve, config: DetrendConfig | None = None, mask: np.ndarray | None = None
) -> DetrendResult:
    """Divide out stellar/instrumental variability.

    Parameters
    ----------
    lc : normalised light curve (flux ~ 1; wotan's slider requires positive flux).
    config : :class:`DetrendConfig`.
    mask : optional boolean array, True for samples (e.g. known transits) that
        must not influence the trend. The trend is still evaluated there.
    """
    from wotan import flatten  # numba-compiled; imported lazily to keep imports fast

    config = config or DetrendConfig()
    if config.method not in TIME_WINDOWED_METHODS:
        raise ValueError(
            f"method {config.method!r} is not a time-windowed slider; "
            f"choose from {sorted(TIME_WINDOWED_METHODS)}"
        )
    finite = np.isfinite(lc.time) & np.isfinite(lc.flux) & np.isfinite(lc.flux_err)
    if mask is not None:
        mask = np.asarray(mask, dtype=bool)
        if mask.size != len(lc):
            raise ValueError("mask must have the same length as the light curve")
        mask = mask[finite]
    lc = lc.select(finite)
    kwargs: dict[str, Any] = {
        "window_length": config.window_length,
        "method": config.method,
        "break_tolerance": config.break_tolerance,
        "edge_cutoff": config.edge_cutoff,
        "return_trend": True,
    }
    if config.cval is not None:
        kwargs["cval"] = config.cval
    if mask is not None and mask.any():
        kwargs["mask"] = mask

    _, trend = flatten(lc.time, lc.flux, **kwargs)
    trend = _fill_trend(lc.time, np.asarray(trend, dtype=float), config.break_tolerance)
    good = np.isfinite(trend) & (trend > 0)

    raw = lc.select(good)
    trend = trend[good]
    meta = dict(lc.meta)
    meta["detrend"] = asdict(config)
    meta["detrend_masked_points"] = 0 if mask is None else int(mask[good].sum())
    flat = LightCurve(raw.time, raw.flux / trend, raw.flux_err / trend, raw.sector, meta)
    return DetrendResult(
        flat=flat,
        trend=trend,
        raw=raw,
        mask=None if mask is None else mask[good],
        config=config,
    )


# --------------------------------------------------------------------------- plots
def observing_seasons(time: np.ndarray, max_gap: float = 10.0) -> list[tuple[int, int]]:
    """Group samples into runs of consecutive sectors separated by < ``max_gap`` days."""
    return segment_bounds(time, max_gap)


def plot_detrending(
    result: DetrendResult,
    path: str | Path,
    title: str | None = None,
    bin_minutes: float = 30.0,
    max_rows: int = 8,
) -> Path:
    """Raw flux with the fitted trend (left) and the flattened flux (right).

    One row per observing season (runs of adjacent sectors), so multi-year
    light curves remain readable.
    """
    seasons = observing_seasons(result.flat.time)
    if len(seasons) > max_rows:
        # Keep the plot legible: show the seasons with the most data.
        sizes = [stop - start for start, stop in seasons]
        keep = sorted(np.argsort(sizes)[-max_rows:])
        seasons = [seasons[i] for i in keep]
    rows = len(seasons)
    cfg = result.config
    with style():
        fig, axes = new_figure(rows, 2, figsize=(12, 2.2 * rows + 0.6), sharey="col")
        for row, (start, stop) in enumerate(seasons):
            sl = slice(start, stop)
            t = result.raw.time[sl]
            ax_raw, ax_flat = axes[row]
            ax_raw.plot(
                t,
                (result.raw.flux[sl] - 1) * 1e3,
                ".",
                ms=1,
                color=INK_MUTED,
                alpha=0.6,
                rasterized=True,
                label="PDCSAP flux",
            )
            tg, trend_g = break_at_gaps(t, (result.trend[sl] - 1) * 1e3, cfg.break_tolerance)
            ax_raw.plot(tg, trend_g, "-", lw=1.2, color=ORANGE, label="trend")
            flat = result.flat.flux[sl]
            ax_flat.plot(
                t,
                (flat - 1) * 1e3,
                ".",
                ms=1,
                color=INK_MUTED,
                alpha=0.6,
                rasterized=True,
                label="flattened",
            )
            tb, fb, _, _ = bin_timeseries(t, flat, width=bin_minutes / 1440.0)
            ax_flat.plot(
                tb, (fb - 1) * 1e3, ".", ms=2.5, color=BLUE, label=f"{bin_minutes:g}-min bins"
            )
            sectors = (
                sorted(set(result.raw.sector[sl].tolist())) if result.raw.sector is not None else []
            )
            label = (
                f"sectors {sectors[0]}–{sectors[-1]}"
                if len(sectors) > 1
                else (f"sector {sectors[0]}" if sectors else "")
            )
            ax_raw.set_title(label, loc="left", fontsize=9)
            ax_raw.set_ylabel("flux − 1 (ppt)")
            ax_flat.set_ylabel("flattened flux − 1 (ppt)")
        for ax in axes[0]:
            ax.legend(
                loc="lower right",
                bbox_to_anchor=(1.0, 1.0),
                ncol=2,
                markerscale=5,
                borderaxespad=0.1,
            )
        axes[-1, 0].set_xlabel("time (BTJD days)")
        axes[-1, 1].set_xlabel("time (BTJD days)")
        suptitle = title or "Detrending"
        fig.suptitle(
            f"{suptitle} — {cfg.method}, window {cfg.window_length:g} d",
            x=0.01,
            ha="left",
            fontsize=12,
            fontweight="bold",
        )
        return save_figure(fig, path)


def break_at_gaps(x: np.ndarray, y: np.ndarray, max_gap: float) -> tuple[np.ndarray, np.ndarray]:
    """Insert NaNs at gaps wider than ``max_gap`` so line plots do not bridge them."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    gaps = np.flatnonzero(np.diff(x) > max_gap) + 1
    if gaps.size == 0:
        return x, y
    return np.insert(x, gaps, np.nan), np.insert(y, gaps, np.nan)


def sector_summary(lc: LightCurve) -> Sequence[dict[str, Any]]:
    """Per-sector point counts and robust scatter (ppm) of a light curve."""
    if lc.sector is None:
        return [{"sector": None, "n": len(lc), "rms_ppm": robust_std(lc.flux) * 1e6}]
    out = []
    for s in lc.sectors:
        sel = lc.sector == s
        out.append({"sector": s, "n": int(sel.sum()), "rms_ppm": robust_std(lc.flux[sel]) * 1e6})
    return out
