"""Box Least Squares (BLS) transit search, including iterative multi-planet search.

Method
------
BLS (Kovacs, Zucker & Mazeh 2002) folds the light curve at each trial period
and fits a box-shaped dip of every trial duration and phase; the best box at
each period defines the periodogram. We use astropy's implementation with the
log-likelihood objective (for white noise, ``0.5 * (depth / sigma_depth)^2``).

Period grid. If the trial frequency is off by ``df``, successive transits drift
in phase and, across a baseline ``B``, the folded transit is smeared by
``B * P * df``. Keeping the smear below ``D / OS`` for a transit of duration
``D`` gives a step uniform in ``log f``::

    d(ln f) = D_min / (OS * B)

(cf. Ofir 2014). Because astropy's cost per trial period grows with
``P / D_min``, the period range is split into logarithmic bands, and each band
only tests durations that are physically possible there: for a circular orbit
the central-transit duration is ``T ~ (P / pi) asin(R*/a)`` with
``a/R* = (G rho* P^2 / 3 pi)^(1/3)``, so a range of stellar densities bounds the
durations worth testing at each period. Long-period bands then use longer
minimum durations, coarser phase bins, and far fewer trial periods.

Detection statistics. From the log-likelihood spectrum we form an S/N-like
spectrum ``sqrt(2 * dlogL)``, remove its slow trend with period (noise peaks
grow with period because there are more phases to try), and standardise it:
the Signal Detection Efficiency is ``SDE = (peak - mean) / std``. The trend,
mean and standard deviation come from the trial periods whose best box holds
at least ``min_transits`` transits with data, the condition a detection must
meet (see :func:`eligible_trials`). In a light curve spread thinly over years,
the best box at most long trial periods covers a single dip; such trials can
never be detections, and left in, their scatter would set the scale against
which every real signal is measured. We also
compute a red-noise-aware transit S/N from the out-of-transit scatter binned to
the transit duration (Pont et al. 2006). A signal counts as a detection only if
both exceed their thresholds and at least ``min_transits`` transits contain data.

Dips at the edges of the data. Before each pass, single dips whose box S/N
reaches ``edge_event_sigma`` but which the data do not cover inside and on both
sides are masked (see :func:`edge_events`). In real TESS light curves such dips
are almost always instrumental: thermal settling after a data downlink,
scattered light, or a momentum dump, at the edge of a segment where the
detrending window is one-sided. They are harmful beyond their own false alarms.
A box can be placed on a strong single dip at every trial period, which raises
the periodogram far above its usual level at long periods, and two such dips,
years apart, pair up into a convincing long-period "planet". A real transit
lost this way is one the vetting would not count either (see its coverage
test).

Iterative search. After a detection, points within ``mask_factor / 2``
durations of each of its transits are removed and BLS is run again, which
reveals shallower planets in multi-planet systems.
"""

from __future__ import annotations

import itertools
import logging
import math
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from astropy.timeseries import BoxLeastSquares
from scipy.signal import find_peaks

from . import progress
from .detrend import DetrendConfig, detrend, ephemeris_mask
from .lightcurve import LightCurve
from .plotting import (
    BLUE,
    INK_MUTED,
    INK_SECONDARY,
    ORANGE,
    format_log_axis,
    new_figure,
    save_figure,
    style,
)
from .utils import (
    DAY,
    RHO_SUN,
    G,
    bin_timeseries,
    binned_rms,
    epoch_index,
    fold,
    segment_bounds,
    transit_mask,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchConfig:
    """BLS search settings. Durations and periods are in days.

    Attributes
    ----------
    min_period, max_period : trial period range; ``max_period=None`` means half
        the time baseline, so that at least two transits can fall in the data.
    min_duration, max_duration, duration_ratio : geometric grid of trial
        durations (consecutive durations differ by ``duration_ratio``).
    frequency_oversample : ``OS`` in the phase-drift criterion above.
    bls_oversample : phase bins per shortest trial duration (astropy).
    rho_min, rho_max : stellar densities (solar units) bounding the durations
        tested at each period when the host density is unknown.
    stellar_density, density_margin : if the host's mean density (solar units)
        is known, only durations possible for densities within a factor
        ``density_margin`` of it are tested. This is much faster at long periods.
    bands_per_decade : number of period bands per decade of period.
    bin_minutes : bin the light curve to this cadence before the search
        (0 disables). Long-period bands, whose shortest trial duration is long,
        use proportionally coarser bins (about a third of that duration).
        Candidate parameters are always refined on unbinned data.
    min_transits : minimum number of transits containing data.
    sde_threshold : minimum SDE of a detection.
    snr_threshold : minimum red-noise S/N of a detection. The threshold actually
        applied is the larger of this and the trial-corrected value
        ``sqrt(2 ln(N_trials / false_alarm_probability))`` (see
        :func:`effective_trials`), so long multi-sector searches, which try many
        more periods and phases, need stronger signals.
    false_alarm_probability : per-light-curve false-alarm probability (for
        white Gaussian noise) used for the trial-corrected S/N threshold.
    max_brightening_ratio : a peak is rejected as stellar variability when the
        light curve folded at its period brightens somewhere, over a box of the
        peak's duration, with more than this fraction of the dip's significance
        (see :func:`folded_brightening`).
    edge_event_sigma : single dips at least this significant (box S/N against
        the red noise on the dip's own timescale) that the data do not cover
        inside and on both sides are masked before each pass (0 disables; see
        :func:`edge_events`).
    max_signals : maximum number of iterations of the multi-planet search.
    mask_factor : width (in transit durations) masked around each transit of a
        detected signal before the next iteration.
    n_workers : processes used for the BLS (1 = serial).
    """

    min_period: float = 0.5
    max_period: float | None = None
    min_duration: float = 0.5 / 24
    max_duration: float = 12.0 / 24
    duration_ratio: float = 1.2
    frequency_oversample: float = 3.0
    bls_oversample: int = 10
    rho_min: float = 0.05
    rho_max: float = 60.0
    stellar_density: float | None = None
    density_margin: float = 3.0
    bands_per_decade: int = 8
    bin_minutes: float = 10.0
    min_transits: int = 2
    sde_threshold: float = 7.0
    snr_threshold: float = 7.0
    false_alarm_probability: float = 0.01
    max_brightening_ratio: float = 0.65
    edge_event_sigma: float = 7.0
    max_signals: int = 5
    mask_factor: float = 2.0
    n_workers: int = 1

    def density_bounds(self) -> tuple[float, float]:
        """Range of stellar densities (solar units) used to bound trial durations."""
        rho = self.stellar_density
        if rho is not None and math.isfinite(rho) and rho > 0:
            return rho / self.density_margin, rho * self.density_margin
        return self.rho_min, self.rho_max


# --------------------------------------------------------------------------- grids
def central_duration(period: np.ndarray | float, rho_solar: float) -> np.ndarray:
    """Duration (days) of a central transit of a small planet, circular orbit."""
    period = np.asarray(period, dtype=float)
    a_rs = (G * rho_solar * RHO_SUN * (period * DAY) ** 2 / (3.0 * math.pi)) ** (1.0 / 3.0)
    return period / math.pi * np.arcsin(np.clip(1.0 / a_rs, 0.0, 1.0))


def duration_grid(config: SearchConfig) -> np.ndarray:
    """Geometric grid of trial durations between ``min_duration`` and ``max_duration``."""
    ratio = math.log(config.max_duration / config.min_duration) / math.log(config.duration_ratio)
    n = math.floor(ratio + 1e-9) + 1
    grid = config.min_duration * config.duration_ratio ** np.arange(n)
    return grid[grid <= config.max_duration * (1 + 1e-9)]


@dataclass
class PeriodBand:
    """A contiguous block of trial periods searched with one duration subset."""

    periods: np.ndarray
    durations: np.ndarray
    bin_width: float = 0.0  # days; 0 = unbinned


@dataclass
class PeriodGrid:
    bands: list[PeriodBand]
    baseline: float

    @property
    def periods(self) -> np.ndarray:
        return np.concatenate([b.periods for b in self.bands])

    @property
    def size(self) -> int:
        return int(sum(b.periods.size for b in self.bands))


# Largest transit duty cycle considered; also guarantees duration < period for astropy.
_MAX_DUTY = 0.25
# Shortest duration considered at a period, as a fraction of the central-transit
# duration around the densest allowed star (i.e. an impact parameter b ~ 0.95).
_GRAZING_FRACTION = 0.3
# Longest duration: central transit around the least dense star, with (1 + Rp/R*) <= 1.2.
_LONG_FACTOR = 1.2


def make_period_grid(baseline: float, config: SearchConfig) -> PeriodGrid:
    """Build the banded period/duration grid described in the module docstring."""
    pmin = config.min_period
    pmax = config.max_period if config.max_period is not None else 0.5 * baseline
    if pmax <= pmin:
        raise ValueError(
            f"max period ({pmax:.3g} d) must exceed min period ({pmin:.3g} d); "
            "is the baseline long enough?"
        )
    durations = duration_grid(config)
    rho_lo, rho_hi = config.density_bounds()
    n_bands = max(1, math.ceil(math.log10(pmax / pmin) * config.bands_per_decade))
    edges = np.geomspace(pmin, pmax, n_bands + 1)
    bands = []
    for i, (lo, hi) in enumerate(itertools.pairwise(edges)):
        d_lo = max(config.min_duration, _GRAZING_FRACTION * float(central_duration(lo, rho_hi)))
        d_hi = min(config.max_duration, _LONG_FACTOR * float(central_duration(hi, rho_lo)))
        d_hi = min(d_hi, _MAX_DUTY * lo)
        # One grid step of margin below the shortest physical duration (grazing
        # geometries are uncertain); none above the longest, which already includes
        # the (1 + Rp/R*) factor and the stellar-density margin.
        sel = (durations >= d_lo / config.duration_ratio) & (durations <= d_hi * (1 + 1e-9))
        sel &= durations < _MAX_DUTY * lo
        band_durations = durations[sel]
        if band_durations.size == 0:
            band_durations = durations[durations < _MAX_DUTY * lo][:1]
        if band_durations.size == 0:
            raise ValueError(f"no trial duration fits periods near {lo:.3g} d")
        step = band_durations.min() / (config.frequency_oversample * baseline)  # d(ln f)
        n = max(2, math.ceil(math.log(hi / lo) / step))
        # Uniform in ln(f); drop the upper edge except in the last band to avoid duplicates.
        ln_f = np.linspace(-math.log(lo), -math.log(hi), n + 1)
        if i < n_bands - 1:
            ln_f = ln_f[:-1]
        periods = np.sort(np.exp(-ln_f))
        bands.append(PeriodBand(periods, band_durations, _band_bin_width(band_durations, config)))
    return PeriodGrid(bands, baseline)


def effective_trials(grid: PeriodGrid) -> float:
    """Approximate number of statistically independent (period, phase, duration) trials.

    At duration ``D`` two trial frequencies give independent folds when they
    differ by ``D / (B P)`` (the phase-drift criterion with no oversampling), so a
    band spanning ``ln(P_hi / P_lo)`` contains ``(B / D) ln(P_hi / P_lo)``
    independent frequencies, each with ``P / D`` independent phases. Durations
    within a factor of two of each other are strongly correlated and are counted
    once per factor of two.
    """
    total = 0.0
    for band in grid.bands:
        lo, hi = float(band.periods.min()), float(band.periods.max())
        d = band.durations
        d_eff = float(np.exp(np.mean(np.log(d))))
        n_dur = 1.0 + math.log(d.max() / d.min()) / math.log(2.0)
        width = math.log(hi / lo) if hi > lo else 0.0
        total += (grid.baseline / d_eff) * width * (math.sqrt(lo * hi) / d_eff) * n_dur
    return max(total, 1.0)


def trial_corrected_threshold(n_trials: float, false_alarm_probability: float) -> float:
    """S/N exceeded by the maximum of ``n_trials`` independent standard normal
    variables with probability ``false_alarm_probability`` (a slightly conservative
    approximation, ``sqrt(2 ln(n / p))``)."""
    return math.sqrt(2.0 * math.log(max(n_trials, 1.0) / false_alarm_probability))


def _band_bin_width(durations: np.ndarray, config: SearchConfig) -> float:
    """Search-binning width for a band: the base width, or a multiple of it up to D_min / 3."""
    if config.bin_minutes <= 0:
        return 0.0
    base = config.bin_minutes / 1440.0
    for factor in (6, 3, 2):
        if factor * base <= durations.min() / 3.0:
            return factor * base
    return base


# --------------------------------------------------------------------------- single events
# A dip counts as covered by the data under the same rule as the vetting's
# coverage test: 75 % of the expected cadences inside it (VetConfig.coverage_min)
# and half of them in a one-duration flank on either side.
_COVERED_INSIDE = 0.75
_COVERED_FLANK = 0.5


def single_events(lc: LightCurve, durations: np.ndarray, min_snr: float) -> list[dict[str, float]]:
    """Individual dips whose depth is at least ``min_snr`` times its uncertainty.

    For every duration ``D`` the flux is averaged in boxes ``D`` wide centred
    every ``D / 4``; boxes holding fewer than half the expected cadences are
    skipped. A box's uncertainty is the scatter of ``D``-long averages in its
    sector (:func:`binned_rms`, which includes red noise), scaled up by the
    square root of the share of cadences it lacks. Local maxima of the S/N are
    kept, strongest first, and a weaker dip within the longer of the two
    durations of a stronger one is dropped. Returns dicts with ``time``,
    ``duration``, ``depth`` and ``snr``.
    """
    t = lc.time
    if t.size < 10:
        return []
    y = np.median(lc.flux) - lc.flux  # positive in a dip
    cum = np.concatenate([[0.0], np.cumsum(y)])
    groups = (
        [np.ones(t.size, dtype=bool)]
        if lc.sector is None
        else [lc.sector == s for s in np.unique(lc.sector)]
    )
    cadence = lc.cadence
    found = []
    for duration in durations:
        sigma = np.full(t.size, np.nan)
        for members in groups:
            sigma[members] = binned_rms(t[members], lc.flux[members], duration)
        centres = np.arange(t[0], t[-1], duration / 4.0)
        lo = np.searchsorted(t, centres - duration / 2.0)
        hi = np.searchsorted(t, centres + duration / 2.0)
        n = hi - lo
        expected = max(duration / cadence, 1.0)
        err = sigma[np.clip(np.searchsorted(t, centres), 0, t.size - 1)] * np.sqrt(
            expected / np.maximum(n, 1)
        )
        ok = (n >= 0.5 * expected) & np.isfinite(err) & (err > 0)
        depth = np.zeros(centres.size)
        depth[ok] = (cum[hi[ok]] - cum[lo[ok]]) / n[ok]
        snr = np.full(centres.size, -1e9)
        snr[ok] = depth[ok] / err[ok]
        peaks, _ = find_peaks(snr, distance=4)
        for i in peaks[snr[peaks] >= min_snr]:
            found.append(
                {
                    "time": float(centres[i]),
                    "duration": float(duration),
                    "depth": float(depth[i]),
                    "snr": float(snr[i]),
                }
            )
    found.sort(key=lambda e: -e["snr"])
    events: list[dict[str, float]] = []
    for e in found:
        if all(abs(e["time"] - k["time"]) >= max(e["duration"], k["duration"]) for k in events):
            events.append(e)
    return events


def edge_events(lc: LightCurve, config: SearchConfig) -> list[dict[str, float]]:
    """Strong single dips (see :func:`single_events`) that the data do not fully cover.

    The trial durations are the search's; the threshold is
    ``config.edge_event_sigma``. A dip is covered if the data hold 75 % of the
    expected cadences inside it and half of them within one duration on either
    side, the vetting's coverage criterion.
    """
    if config.edge_event_sigma <= 0 or len(lc) < 10:
        return []
    cadence = lc.cadence
    out = []
    for event in single_events(lc, duration_grid(config), config.edge_event_sigma):
        width = event["duration"]
        x = lc.time[np.abs(lc.time - event["time"]) < 1.5 * width] - event["time"]
        expected = width / cadence
        inside = np.sum(np.abs(x) < width / 2.0) / expected
        before = np.sum(x < -width / 2.0) / expected
        after = np.sum(x > width / 2.0) / expected
        if inside < _COVERED_INSIDE or before < _COVERED_FLANK or after < _COVERED_FLANK:
            out.append(event)
    return out


def mask_edge_events(
    lc: LightCurve, config: SearchConfig
) -> tuple[LightCurve, list[dict[str, float]]]:
    """``lc`` without its edge events (see :func:`edge_events`), and the events.

    Each event is masked over ``mask_factor`` of its durations, like a detected
    transit.
    """
    events = edge_events(lc, config)
    return without_events(lc, events, config.mask_factor), events


def without_events(
    lc: LightCurve, events: list[dict[str, float]], mask_factor: float
) -> LightCurve:
    """``lc`` without the data within ``mask_factor / 2`` durations of each event."""
    if not events:
        return lc
    keep = np.ones(len(lc), dtype=bool)
    for event in events:
        keep &= np.abs(lc.time - event["time"]) >= 0.5 * mask_factor * event["duration"]
    return lc.select(keep)


# --------------------------------------------------------------------------- BLS core
_WORKER_BLS: list[BoxLeastSquares] = []


def _init_worker(datasets: list[tuple[np.ndarray, np.ndarray, np.ndarray]]) -> None:
    global _WORKER_BLS
    _WORKER_BLS = [BoxLeastSquares(t, y, dy) for t, y, dy in datasets]


def _run_chunk(task: tuple[int, np.ndarray, np.ndarray, int]) -> dict[str, np.ndarray]:
    index, periods, durations, oversample = task
    return _power(_WORKER_BLS[index], periods, durations, oversample)


def _power(
    bls: BoxLeastSquares, periods: np.ndarray, durations: np.ndarray, oversample: int
) -> dict[str, np.ndarray]:
    res = bls.power(periods, durations, objective="likelihood", oversample=oversample)
    return {
        "period": np.asarray(res.period, dtype=float),
        "power": np.asarray(res.power, dtype=float),
        "depth": np.asarray(res.depth, dtype=float),
        "depth_err": np.asarray(res.depth_err, dtype=float),
        "duration": np.asarray(res.duration, dtype=float),
        "t0": np.asarray(res.transit_time, dtype=float),
        "depth_snr": np.asarray(res.depth_snr, dtype=float),
    }


@dataclass
class Periodogram:
    """BLS periodogram (arrays sorted by period)."""

    period: np.ndarray
    power: np.ndarray
    depth: np.ndarray
    depth_err: np.ndarray
    duration: np.ndarray
    t0: np.ndarray
    depth_snr: np.ndarray
    sde: np.ndarray = field(default_factory=lambda: np.array([]))
    n_trials: float = float("nan")
    snr_threshold: float = float("nan")
    edge_events: list[dict[str, float]] = field(default_factory=list)
    eligible: np.ndarray = field(default_factory=lambda: np.array([], dtype=bool))

    def __len__(self) -> int:
        return int(self.period.size)


def sde_spectrum(
    period: np.ndarray,
    power: np.ndarray,
    bins_per_decade: int = 20,
    reference: np.ndarray | None = None,
) -> np.ndarray:
    """Standardised, detrended S/N-like spectrum (the SDE at every trial period).

    The trend is the median of ``sqrt(2 * power)`` in bins of equal width in
    log-period (``bins_per_decade``), interpolated; the residual is
    standardised by its mean and standard deviation. If ``reference`` (a
    boolean mask) is given, only those trials define the trend, mean and
    standard deviation, which are then applied to every trial.

    Equal *width* in log-period matters. A strong transit raises the spectrum
    over a broad range of nearby trial periods (subsets of its transits still
    line up), and a narrow bin around the true period would take that hump as
    its "trend". The signal would then depress its own SDE and could lose to
    its P/2 or 2P alias. With ~12 % wide bins the hump is a minority of any
    bin and the median ignores it.
    """
    snr = np.sqrt(2.0 * np.clip(power, 0.0, None))
    ref = np.ones(snr.size, dtype=bool) if reference is None else np.asarray(reference, bool)
    if ref.sum() < 10:
        ref = np.ones(snr.size, dtype=bool)
    if snr.size < 10:
        return (snr - snr.mean()) / (snr.std() or 1.0)
    log_p = np.log10(period)
    n_bins = max(3, round((log_p.max() - log_p.min()) * bins_per_decade))
    edges = np.linspace(log_p.min(), log_p.max(), n_bins + 1)
    which = np.clip(np.searchsorted(edges, log_p, side="right") - 1, 0, n_bins - 1)
    centers, medians = [], []
    for k in range(n_bins):
        members = (which == k) & ref
        if members.sum() >= 5:
            centers.append(np.median(log_p[members]))
            medians.append(np.median(snr[members]))
    if len(centers) < 2:
        trend = np.full(snr.size, np.median(snr[ref]))
    else:
        trend = np.interp(log_p, centers, medians)
    resid = snr - trend
    std = resid[ref].std()
    return (resid - resid[ref].mean()) / (std if std > 0 else 1.0)


def eligible_trials(
    time: np.ndarray,
    period: np.ndarray,
    t0: np.ndarray,
    duration: np.ndarray,
    min_transits: int = 2,
    min_fraction: float = 0.5,
    max_gap: float = 0.5,
) -> np.ndarray:
    """Whether each trial box ``(period, t0, duration)`` holds ``min_transits`` transits with data.

    A transit has data if its box holds at least ``min_fraction`` of the
    expected cadences, the criterion of :func:`count_transits_with_data`. Up to
    the period ``P_safe`` every trial qualifies without counting: two stretches
    of data (separated by gaps longer than ``max_gap`` days) that are both
    longer than ``P + D`` contain a whole box at every phase, and so does one
    stretch longer than ``2 P + D`` twice. The rest are counted on a grid of
    cadence-wide bins. Small gaps inside a stretch are ignored below
    ``P_safe``, which only matters for standardising the spectrum; a detection
    is always checked transit by transit.
    """
    time = np.sort(np.asarray(time, dtype=float))
    period = np.asarray(period, dtype=float)
    out = np.ones(period.size, dtype=bool)
    if time.size < 2 or period.size == 0:
        return out
    stretches = sorted(
        (time[b - 1] - time[a] for a, b in segment_bounds(time, max_gap)), reverse=True
    )
    d_max = float(np.max(duration))
    longest, second = stretches[0], (stretches[1] if len(stretches) > 1 else 0.0)
    p_safe = max(second - d_max, (longest - d_max) / 2.0) if min_transits <= 2 else 0.0
    todo = np.flatnonzero(period > p_safe)
    if todo.size == 0:
        return out
    cadence = float(np.median(np.diff(time)))
    t_min, t_max = time[0], time[-1]
    counts = np.bincount(((time - t_min) / cadence).astype(np.int64))
    cum = np.concatenate([[0], np.cumsum(counts)])
    t0 = np.asarray(t0, dtype=float)
    duration = np.asarray(duration, dtype=float)
    # Chunks of about a million (trial, epoch) pairs.
    span = t_max - t_min
    per_trial = span / period[todo] + 2
    bounds = np.searchsorted(np.cumsum(per_trial), np.arange(1e6, per_trial.sum() + 1e6, 1e6))
    for chunk in np.split(todo, np.unique(bounds[bounds < todo.size])):
        p, t, d = period[chunk], t0[chunk], duration[chunk]
        first = np.ceil((t_min - t) / p).astype(np.int64)
        n_epochs = np.maximum(np.floor((t_max - t) / p).astype(np.int64) - first + 1, 0)
        trial = np.repeat(np.arange(chunk.size), n_epochs)
        epoch = (
            first[trial]
            + np.arange(trial.size)
            - np.repeat(np.cumsum(n_epochs) - n_epochs, n_epochs)
        )
        centre = t[trial] + epoch * p[trial]
        lo = np.clip(((centre - d[trial] / 2 - t_min) / cadence).astype(np.int64), 0, cum.size - 1)
        hi = np.clip(((centre + d[trial] / 2 - t_min) / cadence).astype(np.int64), 0, cum.size - 1)
        covered = (cum[hi] - cum[lo]) >= min_fraction * d[trial] / cadence
        out[chunk] = np.bincount(trial[covered], minlength=chunk.size) >= min_transits
    return out


def bls_periodogram(
    lc: LightCurve, config: SearchConfig, baseline: float | None = None
) -> Periodogram:
    """Evaluate the BLS periodogram of ``lc`` over the banded grid.

    ``baseline`` defaults to the light curve's own time span; iterative
    searches pass the original baseline so the grid does not change when
    transits are masked.
    """
    baseline = lc.baseline if baseline is None else baseline
    grid = make_period_grid(baseline, config)

    # One (binned) copy of the data per distinct band bin width.
    widths = sorted({band.bin_width for band in grid.bands})
    datasets = []
    for width in widths:
        binned = lc.bin(width) if width > 0 else lc
        datasets.append((binned.time, binned.flux, binned.flux_err))
    log.info(
        "BLS: %d trial periods in %d bands; %s points after binning",
        grid.size,
        len(grid.bands),
        "/".join(str(d[0].size) for d in datasets),
    )

    # Chunks of roughly equal cost (points + phase bins * durations per period).
    tasks = []
    for band in grid.bands:
        index = widths.index(band.bin_width)
        n_points = datasets[index][0].size
        per_period = (
            n_points
            + band.periods.mean()
            / (band.durations.min() / config.bls_oversample)
            * band.durations.size
        )
        chunk = int(np.clip(2e8 / per_period, 50, 20000))
        for start in range(0, band.periods.size, chunk):
            tasks.append(
                (index, band.periods[start : start + chunk], band.durations, config.bls_oversample)
            )

    n_workers = max(1, int(config.n_workers))
    results = []
    if n_workers == 1 or len(tasks) == 1:
        engines = [BoxLeastSquares(*d) for d in datasets]
        for i, p, d, o in tasks:
            results.append(_power(engines[i], p, d, o))
            progress.report("bls", done=len(results), total=len(tasks))
    else:
        with ProcessPoolExecutor(
            max_workers=n_workers, initializer=_init_worker, initargs=(datasets,)
        ) as pool:
            for result in pool.map(_run_chunk, tasks):
                results.append(result)
                progress.report("bls", done=len(results), total=len(tasks))

    merged = {k: np.concatenate([r[k] for r in results]) for k in results[0]}
    order = np.argsort(merged["period"])
    merged = {k: v[order] for k, v in merged.items()}
    pg = Periodogram(**merged)
    pg.eligible = eligible_trials(
        lc.time, pg.period, pg.t0, pg.duration, min_transits=config.min_transits
    )
    pg.sde = sde_spectrum(pg.period, pg.power, reference=pg.eligible)
    pg.n_trials = effective_trials(grid)
    pg.snr_threshold = max(
        config.snr_threshold,
        trial_corrected_threshold(pg.n_trials, config.false_alarm_probability),
    )
    return pg


# --------------------------------------------------------------------------- signals
@dataclass
class Signal:
    """A periodic transit-like signal found by BLS.

    ``depth`` is the mean in-transit flux deficit of the best box (it
    underestimates the maximum depth of a limb-darkened transit). ``snr`` is
    the red-noise-aware S/N; ``snr_white`` assumes white noise.
    """

    iteration: int
    period: float
    t0: float
    duration: float
    depth: float
    depth_err: float
    snr: float
    snr_white: float
    sde: float
    power: float
    n_transits: int
    detected: bool = False
    snr_threshold: float = float("nan")
    harmonic_of: int | None = None
    secondary_of: int | None = None
    phase_offset: float = float("nan")
    brightening_ratio: float = float("nan")
    skipped_peaks: list[dict[str, Any]] = field(default_factory=list)
    depth_odd: float = float("nan")
    depth_odd_err: float = float("nan")
    depth_even: float = float("nan")
    depth_even_err: float = float("nan")
    transit_times: list[float] = field(default_factory=list)

    @property
    def rp_rs_estimate(self) -> float:
        """Radius ratio implied by the box depth (depth ~ (Rp/R*)^2)."""
        return math.sqrt(max(self.depth, 0.0))

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["rp_rs_estimate"] = self.rp_rs_estimate
        return out


def count_transits_with_data(
    time: np.ndarray, period: float, t0: float, duration: float, min_fraction: float = 0.5
) -> int:
    """Number of individual transits covered by at least ``min_fraction`` of their points."""
    time = np.asarray(time, dtype=float)
    in_tr = transit_mask(time, period, t0, duration)
    if not in_tr.any():
        return 0
    cadence = np.median(np.diff(time)) if time.size > 1 else duration
    expected = max(duration / cadence, 1.0)
    _, counts = np.unique(epoch_index(time[in_tr], period, t0), return_counts=True)
    return int(np.sum(counts >= max(1.0, min_fraction * expected)))


def red_noise_snr(
    lc: LightCurve, period: float, t0: float, duration: float, depth: float, n_transits: int
) -> float:
    """Transit S/N using the out-of-transit scatter on the transit timescale.

    ``sigma_D`` is the scatter of the flux averaged over windows of one
    transit duration; with ``N`` transits the depth uncertainty is
    ``sigma_D / sqrt(N)``. This includes correlated noise that a per-point
    white-noise estimate would miss.
    """
    oot = ~transit_mask(lc.time, period, t0, 2.0 * duration)
    sigma = binned_rms(lc.time[oot], lc.flux[oot], duration)
    if not np.isfinite(sigma) or sigma <= 0 or n_transits < 1:
        return float("nan")
    return float(depth / (sigma / math.sqrt(n_transits)))


def harmonic_relation(
    signal: Signal, previous: list[Signal], tol: float = 0.002, max_n: int = 10
) -> int | None:
    """Index of an earlier signal of which ``signal`` is a harmonic (or alias), else None.

    Two conditions must hold: the period ratio is within ``tol`` (relative) of
    an integer or unit fraction ``n <= max_n``, *and* the transits coincide in
    time with the earlier ephemeris. The timing condition matters because real
    multi-planet systems are often close to (but not exactly in) mean-motion
    resonance -- TOI-270 c and d have a period ratio of ~2.01 -- and such
    planets must not be discarded as aliases of each other.
    """
    for j, prev in enumerate(previous):
        ratio = signal.period / prev.period
        for r in (ratio, 1.0 / ratio):
            n = round(r)
            if not (1 <= n <= max_n and abs(r - n) < tol * n):
                continue
            shorter = min(signal.period, prev.period)
            offset = abs(fold(np.array([signal.t0]), shorter, prev.t0)[0])
            if offset < max(signal.duration, prev.duration):
                return j
    return None


def same_period_relation(
    signal: Signal, previous: list[Signal], tol: float = 0.002, max_n: int = 3
) -> tuple[int, float] | None:
    """Earlier signal whose orbit this signal shares at a *different* phase, if any.

    Returns ``(index, phase)``, where ``phase`` in [0, 1) is the orbital phase of
    this signal's transits relative to the earlier signal. The period must equal
    the earlier one or a unit fraction of it (P/2, P/3): once the earlier
    transits are masked, a secondary eclipse at phase 0.5 folds equally well at
    P/2. The criterion uses the transits that actually contain data. None of
    them may overlap an earlier transit, and all must sit at one phase of the
    earlier period. Two independent planets sharing an orbit are practically
    unknown, so such a pair is the primary and secondary eclipse of one system:
    an eclipsing binary, or a planet and its occultation. The vetting of the
    earlier signal decides which.
    """
    times = np.asarray(signal.transit_times if signal.transit_times else [signal.t0], dtype=float)
    for j, prev in enumerate(previous):
        ratio = prev.period / signal.period
        n = round(ratio)
        if not (1 <= n <= max_n and abs(ratio - n) < tol * n):
            continue
        window = max(signal.duration, prev.duration)
        offsets = fold(times, prev.period, prev.t0)  # time from nearest earlier transit
        if np.any(np.abs(offsets) < window):
            continue  # overlaps the earlier transits: an alias, not another eclipse
        phases = offsets % prev.period
        centre = phases[np.argmin([np.sum(np.abs(fold(phases, prev.period, c))) for c in phases])]
        if np.all(np.abs(fold(phases, prev.period, centre)) < window):
            return j, float(centre / prev.period)
    return None


def folded_brightening(
    lc: LightCurve, period: float, t0: float, duration: float, exclude: float = 2.0
) -> tuple[float, float]:
    """Significance of the dip and of the strongest brightening in the folded light curve.

    The light curve is folded at ``period`` and averaged in a box of width
    ``duration`` at every phase, in steps of a fifth of the duration. The
    reference level is the median of these box averages, which is the
    out-of-transit flux for a transit and the mean for a wave. Returns
    ``(dip, brightening)``: the significance (box average relative to the
    reference, over its white-noise uncertainty) of the box centred on the dip,
    and the largest significance of a box *above* the reference at least
    ``exclude`` durations from the dip (less at duty cycles above 1/6).

    A transiting body only removes light, so a genuine transit leaves the rest of
    the folded light curve flat, and its largest brightening is a noise
    fluctuation of about ``sqrt(2 ln(P / D))`` sigma. A "dip" that is one trough
    of a wave (residual starspot modulation that survives detrending near the
    rotation period) comes with crests of similar significance. Unrelated
    variability at the orbital period adds bumps too, but a transit found at
    S/N >= 7 still stands well above them. This is a variant of the Kepler
    Robovetter's model-shift uniqueness test (Coughlin et al. 2016) restricted to
    brightenings, so that the secondary eclipses of eclipsing binaries do not
    count against them (the vetting stage deals with those). Boxes next to the dip
    are excluded because unmasked detrending leaves small positive "shoulders"
    around transits.
    """
    nan = float("nan")
    t, y, dy = lc.time, lc.flux, lc.flux_err
    w = 1.0 / dy**2
    phase = fold(t, period, t0)
    # Box sums at every phase from cumulative sums over the phase-sorted data,
    # tiled once on either side so that boxes can wrap around +-P/2.
    order = np.argsort(phase)
    ph = np.concatenate([phase[order] - period, phase[order], phase[order] + period])
    cum_w = np.concatenate([[0.0], np.cumsum(np.tile(w[order], 3))])
    cum_wy = np.concatenate([[0.0], np.cumsum(np.tile((w * y)[order], 3))])
    centres = np.arange(0.0, period, 0.2 * duration)
    lo = np.searchsorted(ph, centres - duration / 2)
    hi = np.searchsorted(ph, centres + duration / 2)
    sum_w = cum_w[hi] - cum_w[lo]
    ok = sum_w > 0
    if not ok[0] or ok.sum() < 2:
        return nan, nan
    mean = np.full(centres.size, np.nan)
    mean[ok] = (cum_wy[hi] - cum_wy[lo])[ok] / sum_w[ok]
    level = float(np.nanmedian(mean))
    significance = (mean - level) * np.sqrt(sum_w)
    # At duty cycles above 1/6 the exclusion shrinks so that half the phases remain.
    reach = min(exclude * duration, period / 2 - duration)
    away = ok & (centres >= reach) & (centres <= period - reach)
    if not away.any():
        return float(-significance[0]), nan
    return float(-significance[0]), float(significance[away].max())


def _resolve_harmonic(pg: Periodogram, idx: int, margin: float = 1.2, tol: float = 0.003) -> int:
    """Move to the member of the harmonic family (P/3 ... 3P) with the most power.

    For a genuine transit the log-likelihood peaks at the true period (P/2 and
    2P fold in empty or missing transits and reach about half of it), so a
    related peak with clearly (``margin``) more raw power is the better period.
    """
    base = pg.period[idx]
    best, best_power = idx, pg.power[idx]
    for ratio in (1 / 3, 1 / 2, 2, 3):
        target = base * ratio
        lo, hi = np.searchsorted(pg.period, [target * (1 - tol), target * (1 + tol)])
        if hi <= lo:
            continue
        j = int(lo + np.argmax(pg.power[lo:hi]))
        if pg.power[j] > margin * pg.power[idx] and pg.power[j] > best_power:
            best, best_power = j, pg.power[j]
    return int(best)


def _refine(
    lc: LightCurve, period: float, duration: float, grid_step: float, config: SearchConfig
) -> dict[str, float]:
    """Re-run BLS on unbinned data on a fine grid around a candidate peak."""
    periods = period * np.exp(np.linspace(-4 * grid_step, 4 * grid_step, 81))
    durations = duration * np.geomspace(1 / 1.6, 1.6, 17)
    durations = durations[
        (durations < _MAX_DUTY * periods.min()) & (durations > 0.2 * config.min_duration)
    ]
    bls = BoxLeastSquares(lc.time, lc.flux, lc.flux_err)
    res = _power(bls, periods, durations, max(config.bls_oversample, 20))
    best = int(np.argmax(res["power"]))
    return {k: float(v[best]) for k, v in res.items()}


def _signal_stats(lc: LightCurve, period: float, duration: float, t0: float) -> dict[str, Any]:
    bls = BoxLeastSquares(lc.time, lc.flux, lc.flux_err)
    stats = bls.compute_stats(period, duration, t0)
    counts = np.asarray(stats["per_transit_count"])
    times = np.asarray(stats["transit_times"], dtype=float)
    return {
        "depth": float(stats["depth"][0]),
        "depth_err": float(stats["depth"][1]),
        "depth_odd": float(stats["depth_odd"][0]),
        "depth_odd_err": float(stats["depth_odd"][1]),
        "depth_even": float(stats["depth_even"][0]),
        "depth_even_err": float(stats["depth_even"][1]),
        "transit_times": times[counts > 0].tolist(),
    }


def _central_epoch(time: np.ndarray, period: float, t0: float) -> float:
    """Shift ``t0`` to the transit epoch closest to the middle of the data."""
    n = round((np.median(time) - t0) / period)
    return float(t0 + n * period)


def find_signal(
    lc: LightCurve,
    config: SearchConfig,
    iteration: int = 1,
    baseline: float | None = None,
    previous: list[Signal] | None = None,
) -> tuple[Signal | None, Periodogram]:
    """Run one BLS pass on a flattened light curve and characterise its best peak.

    Strong dips at the edges of the data are masked first (see
    :func:`edge_events`; they are listed in the periodogram's ``edge_events``).
    Peaks are then examined in order of decreasing SDE; the first one with at
    least ``min_transits`` transits containing data is refined on unbinned data.
    """
    baseline = lc.baseline if baseline is None else baseline
    lc, edge = mask_edge_events(lc, config)
    pg = bls_periodogram(lc, config, baseline)
    pg.edge_events = edge
    # Transit coverage of candidate peaks is checked on (lightly) binned data for speed.
    search_lc = lc.bin(config.bin_minutes / 1440.0) if config.bin_minutes > 0 else lc

    order = np.argsort(pg.sde)[::-1]
    order = order[pg.eligible[order]]  # a box on fewer transits can never be a detection
    examined: list[float] = []
    skipped: list[dict[str, Any]] = []
    chosen = None
    chosen_ratio = float("nan")
    for top in order[:5000]:
        if any(abs(pg.period[top] - p) < 0.01 * p for p in examined):
            continue
        examined.append(float(pg.period[top]))
        idx = _resolve_harmonic(pg, int(top))
        period = float(pg.period[idx])
        if idx != top:
            if any(abs(period - p) < 0.01 * p for p in examined):
                continue  # this harmonic family was already examined
            examined.append(period)
        n_tr = count_transits_with_data(search_lc.time, period, pg.t0[idx], pg.duration[idx])
        if n_tr < config.min_transits:
            skipped.append(
                {
                    "period": period,
                    "sde": float(pg.sde[idx]),
                    "reason": f"only {n_tr} transit(s) with data",
                }
            )
        else:
            dip, bright = folded_brightening(search_lc, period, pg.t0[idx], pg.duration[idx])
            ratio = bright / dip if dip > 0 else float("nan")
            if ratio > config.max_brightening_ratio:
                reason = (
                    f"folded light curve also brightens ({bright:.1f} sigma, against "
                    f"{dip:.1f} sigma for the dip): stellar variability"
                )
                skipped.append({"period": period, "sde": float(pg.sde[idx]), "reason": reason})
            else:
                chosen, chosen_ratio = idx, ratio
                break
        if len(examined) >= 25:
            break
    if chosen is None:
        return None, pg

    period, duration = float(pg.period[chosen]), float(pg.duration[chosen])
    # Local log-frequency step of the grid, used to size the refinement window.
    nearby = pg.period[max(chosen - 1, 0) : chosen + 2]
    grid_step = float(np.median(np.abs(np.diff(np.log(nearby))))) if nearby.size > 1 else 1e-4
    refined = _refine(lc, period, duration, max(grid_step, 1e-6), config)
    period, duration, t0 = refined["period"], refined["duration"], refined["t0"]
    t0 = _central_epoch(lc.time, period, t0)
    stats = _signal_stats(lc, period, duration, t0)
    n_transits = count_transits_with_data(lc.time, period, t0, duration)
    snr = red_noise_snr(lc, period, t0, duration, stats["depth"], n_transits)
    snr_white = stats["depth"] / stats["depth_err"] if stats["depth_err"] > 0 else float("nan")
    signal = Signal(
        iteration=iteration,
        period=period,
        t0=t0,
        duration=duration,
        depth=stats["depth"],
        depth_err=stats["depth_err"],
        snr=snr,
        snr_white=float(snr_white),
        sde=float(pg.sde[chosen]),
        power=float(pg.power[chosen]),
        n_transits=n_transits,
        snr_threshold=pg.snr_threshold,
        brightening_ratio=chosen_ratio,
        skipped_peaks=skipped,
        depth_odd=stats["depth_odd"],
        depth_odd_err=stats["depth_odd_err"],
        depth_even=stats["depth_even"],
        depth_even_err=stats["depth_even_err"],
        transit_times=stats["transit_times"],
    )
    signal.detected = bool(
        signal.sde >= config.sde_threshold
        and np.isfinite(signal.snr)
        and signal.snr >= pg.snr_threshold
        and signal.depth > 0
    )
    if previous:
        # Another eclipse of an earlier signal's orbit is checked first: at P/2 it would
        # otherwise also pass for a harmonic (phases 0 and 0.5 coincide modulo P/2).
        same = same_period_relation(signal, previous)
        if same is not None:
            signal.secondary_of, signal.phase_offset = same
        else:
            signal.harmonic_of = harmonic_relation(signal, previous)
    return signal, pg


@dataclass
class SearchResult:
    signals: list[Signal]
    periodograms: list[Periodogram]
    config: SearchConfig
    baseline: float
    n_points: int

    @property
    def detections(self) -> list[Signal]:
        """Signals passing the detection criteria (including secondary eclipses)."""
        return [s for s in self.signals if s.detected]

    @property
    def candidates(self) -> list[Signal]:
        """Detections that are candidate planets: not a secondary eclipse of another."""
        return [s for s in self.detections if s.secondary_of is None]


def iterative_search(
    lc: LightCurve,
    config: SearchConfig | None = None,
    raw: LightCurve | None = None,
    detrend_config: DetrendConfig | None = None,
) -> SearchResult:
    """Search repeatedly, masking each detected signal, until nothing significant remains.

    ``lc`` is the flattened light curve. If the un-detrended light curve ``raw``
    is also given (recommended), every iteration after a detection *re-detrends*
    ``raw`` with all transits found so far masked, instead of only deleting the
    in-transit points. This matters: a windowed detrender run without a mask
    dips under every transit and leaves small positive "shoulders" within half
    a window of it. Those shoulders are coherent at the planet's period and its
    subharmonics and can otherwise be picked up as spurious signals at P/n.

    The last (non-detected) iteration is kept in the result so that the
    strongest sub-threshold peak can be inspected; iteration stops as soon as a
    signal fails the thresholds or ``max_signals`` is reached. A significant
    signal that is a harmonic of an earlier one is masked and recorded, but it
    is not counted as a new planet. A significant signal at the *same* period
    as an earlier one but a different phase stays a detection with
    ``secondary_of`` set (see :func:`same_period_relation`).
    """
    config = config or SearchConfig()
    lc = lc.finite()
    baseline = lc.baseline
    current = lc
    signals: list[Signal] = []
    periodograms: list[Periodogram] = []
    for iteration in range(1, config.max_signals + 1):
        if len(current) < 100:
            break
        progress.report("search_pass", iteration=iteration, max_iterations=config.max_signals)
        signal, pg = find_signal(current, config, iteration, baseline, signals)
        periodograms.append(pg)
        if signal is None:
            break
        significant = signal.detected
        if signal.harmonic_of is not None:
            # Residual power of an earlier signal: mask it too, but it is not a new planet.
            signal.detected = False
        signals.append(signal)
        if not significant:
            break
        if raw is not None:
            mask = ephemeris_mask(raw.time, signals, width_factor=config.mask_factor)
            redone = detrend(raw, detrend_config, mask=mask)
            current = redone.flat.select(~redone.mask)
        else:
            keep = ~transit_mask(
                current.time, signal.period, signal.t0, config.mask_factor * signal.duration
            )
            current = current.select(keep)
    return SearchResult(signals, periodograms, config, baseline, len(lc))


def default_n_workers() -> int:
    """All available cores (respecting CPU affinity where supported)."""
    try:
        return len(os.sched_getaffinity(0))
    except AttributeError:  # pragma: no cover - macOS / Windows
        return os.cpu_count() or 1


# --------------------------------------------------------------------------- plots
def _draw_sde(ax: Any, pg: Periodogram, sde_threshold: float | None, lw: float = 0.7) -> None:
    """SDE against trial period, with trials that can never be detections in grey.

    Those are trials whose best box holds fewer than two transits with data; in a
    light curve spread over years they can tower over everything else, so the
    axis is cut at 1.3 times the highest other peak (or the threshold).
    """
    eligible = pg.eligible if pg.eligible.size == len(pg) else np.ones(len(pg), dtype=bool)
    if not eligible.all():
        ax.plot(
            pg.period,
            np.where(eligible, np.nan, pg.sde),
            "-",
            lw=0.5,
            color=INK_MUTED,
            alpha=0.6,
            rasterized=True,
            label="best box has fewer than two transits with data",
        )
    ax.plot(pg.period, np.where(eligible, pg.sde, np.nan), "-", lw=lw, color=BLUE, rasterized=True)
    if not eligible.all():
        top = max(float(np.max(pg.sde[eligible])) if eligible.any() else 0.0, sde_threshold or 0.0)
        if top > 0 and float(np.max(pg.sde)) > 1.3 * top:
            ax.set_ylim(top=1.3 * top)
        ax.legend(loc="upper left", fontsize=8)


def plot_periodogram(
    pg: Periodogram,
    signal: Signal | None,
    path: str | Path,
    title: str = "",
    sde_threshold: float | None = None,
) -> Path:
    """SDE periodogram with the selected peak and its harmonics marked."""
    with style():
        fig, axes = new_figure(1, 1, figsize=(9, 3.4))
        ax = axes[0, 0]
        _draw_sde(ax, pg, sde_threshold)
        ax.set_xscale("log")
        format_log_axis(ax)
        ax.set_xlabel("trial period (days)")
        ax.set_ylabel("SDE")
        if sde_threshold is not None:
            ax.axhline(sde_threshold, color=INK_MUTED, lw=0.9)
            ax.annotate(
                f"threshold {sde_threshold:g}",
                (pg.period.min(), sde_threshold),
                xytext=(2, 3),
                textcoords="offset points",
                color=INK_SECONDARY,
                fontsize=8,
            )
        if signal is not None:
            lo, hi = pg.period.min(), pg.period.max()
            for n in (0.5, 2.0, 1 / 3, 3.0):
                harmonic = signal.period * n
                if lo <= harmonic <= hi:
                    ax.axvline(harmonic, color=INK_MUTED, lw=0.8, ls=":", zorder=0)
            ax.plot(
                signal.period, signal.sde, "v", ms=8, color=ORANGE, mec="white", mew=1.0, zorder=5
            )
            ax.annotate(
                f"P = {signal.period:.5f} d\nSDE = {signal.sde:.1f}",
                (signal.period, signal.sde),
                xytext=(8, -4),
                textcoords="offset points",
                va="top",
                color=INK_SECONDARY,
                fontsize=8,
            )
        ax.set_title(title or "BLS periodogram", loc="left")
        return save_figure(fig, path)


def plot_folded(
    lc: LightCurve,
    signal: Signal,
    path: str | Path,
    title: str = "",
    window_durations: float = 4.0,
) -> Path:
    """Phase-folded light curve around the transit (left) and over the full orbit (right)."""
    phase = fold(lc.time, signal.period, signal.t0)
    hours = phase * 24.0
    half_window = max(window_durations * signal.duration, 0.1) / 2 * 24.0
    near = np.abs(hours) < half_window
    bin_hours = max(signal.duration * 24.0 / 8.0, 2.0 / 60.0)
    depth_ppm = signal.depth * 1e6
    with style():
        fig, axes = new_figure(1, 2, figsize=(11, 3.8), width_ratios=[1.3, 1])
        ax, ax_full = axes[0]
        ax.plot(
            hours[near],
            (lc.flux[near] - 1) * 1e6,
            ".",
            ms=1.5,
            color=INK_MUTED,
            alpha=0.5,
            rasterized=True,
            label="data",
        )
        hb, fb, eb, _ = bin_timeseries(hours[near], lc.flux[near], width=bin_hours)
        ax.errorbar(
            hb,
            (fb - 1) * 1e6,
            yerr=eb * 1e6,
            fmt="o",
            ms=3.5,
            color=BLUE,
            lw=1,
            label=f"{bin_hours * 60:.0f}-min bins",
        )
        box_x = np.array(
            [
                -half_window,
                -signal.duration * 12,
                -signal.duration * 12,
                signal.duration * 12,
                signal.duration * 12,
                half_window,
            ]
        )
        box_y = np.array([0, 0, -depth_ppm, -depth_ppm, 0, 0])
        ax.plot(box_x, box_y, "-", color=ORANGE, lw=1.6, label="BLS box")
        ax.set_xlim(-half_window, half_window)
        ymin = min(-1.6 * depth_ppm, np.nanpercentile((lc.flux[near] - 1) * 1e6, 0.5))
        ymax = max(0.6 * depth_ppm, np.nanpercentile((lc.flux[near] - 1) * 1e6, 99.5))
        ax.set_ylim(ymin, ymax)
        ax.set_xlabel("hours from mid-transit")
        ax.set_ylabel("flux − 1 (ppm)")
        ax.legend(
            loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=3, markerscale=2, borderaxespad=0.1
        )

        orbital_phase = phase / signal.period
        pb, fbf, _, _ = bin_timeseries(
            orbital_phase, lc.flux, width=max(signal.duration / signal.period / 3, 0.002)
        )
        ax_full.plot(
            orbital_phase,
            (lc.flux - 1) * 1e6,
            ".",
            ms=1,
            color=INK_MUTED,
            alpha=0.3,
            rasterized=True,
        )
        ax_full.plot(pb, (fbf - 1) * 1e6, ".", ms=3, color=BLUE)
        ax_full.set_xlim(-0.5, 0.5)
        ax_full.set_ylim(ymin, ymax)
        ax_full.set_xlabel("orbital phase")
        ax_full.set_title("full orbit", loc="left", fontsize=9)
        label = (
            f"P = {signal.period:.5f} d   T0 = {signal.t0:.4f} BTJD   "
            f"duration = {signal.duration * 24:.2f} h   depth = {depth_ppm:.0f} ppm   "
            f"S/N = {signal.snr:.1f}   SDE = {signal.sde:.1f}"
        )
        fig.suptitle(f"{title}\n{label}" if title else label, x=0.01, ha="left", fontsize=10)
        return save_figure(fig, path)


def plot_search_summary(
    result: SearchResult, lc: LightCurve, path: str | Path, title: str = ""
) -> Path:
    """One row per search iteration: periodogram and folded transit."""
    rows = max(len(result.signals), 1)
    with style():
        fig, axes = new_figure(rows, 2, figsize=(12, 2.8 * rows + 0.5), width_ratios=[1.6, 1])
        for row in range(rows):
            ax_pg, ax_fold = axes[row]
            if row >= len(result.periodograms):
                ax_pg.set_visible(False)
                ax_fold.set_visible(False)
                continue
            pg = result.periodograms[row]
            _draw_sde(ax_pg, pg, result.config.sde_threshold, lw=0.6)
            ax_pg.set_xscale("log")
            format_log_axis(ax_pg)
            ax_pg.axhline(result.config.sde_threshold, color=INK_MUTED, lw=0.9)
            ax_pg.set_ylabel("SDE")
            if row >= len(result.signals):
                ax_fold.set_visible(False)
                continue
            sig = result.signals[row]
            if sig.detected and sig.secondary_of is not None:
                status = f"same period as #{sig.secondary_of + 1}, phase {sig.phase_offset:.2f}"
            elif sig.detected:
                status = "detected"
            elif sig.harmonic_of is not None:
                status = f"harmonic of #{sig.harmonic_of + 1}"
            else:
                status = "below threshold"
            ax_pg.plot(sig.period, sig.sde, "v", ms=7, color=ORANGE, mec="white", mew=1.0)
            ax_pg.set_title(
                f"iteration {sig.iteration}: P = {sig.period:.4f} d, SDE {sig.sde:.1f}, "
                f"S/N {sig.snr:.1f} ({status})",
                loc="left",
                fontsize=9,
            )
            # Show the data this iteration actually searched: earlier signals masked.
            searched = np.ones(len(lc), dtype=bool)
            for prev in result.signals[:row]:
                searched &= ~transit_mask(
                    lc.time, prev.period, prev.t0, result.config.mask_factor * prev.duration
                )
            hours = fold(lc.time, sig.period, sig.t0) * 24
            win = max(3 * sig.duration * 24, 3.0)
            near = (np.abs(hours) < win) & searched
            ax_fold.plot(
                hours[near],
                (lc.flux[near] - 1) * 1e6,
                ".",
                ms=1,
                color=INK_MUTED,
                alpha=0.4,
                rasterized=True,
            )
            hb, fb, _, _ = bin_timeseries(
                hours[near], lc.flux[near], width=max(sig.duration * 3, 0.1)
            )
            ax_fold.plot(hb, (fb - 1) * 1e6, "o", ms=3, color=BLUE)
            ax_fold.set_xlim(-win, win)
            spread = max(2.5 * sig.depth * 1e6, 5 * np.nanstd(fb - 1) * 1e6 if fb.size else 0)
            ax_fold.set_ylim(-spread, 0.8 * spread)
            ax_fold.set_ylabel("flux − 1 (ppm)")
        axes[-1, 0].set_xlabel("trial period (days)")
        axes[-1, 1].set_xlabel("hours from mid-transit")
        fig.suptitle(
            title or "Iterative BLS search", x=0.01, ha="left", fontsize=12, fontweight="bold"
        )
        return save_figure(fig, path)
