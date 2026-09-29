"""Centroid test: is the dip on the target star?

A TESS pixel is 21 arcsec across, so the light of stars around the target falls
into its aperture too, and an eclipsing binary among them can make a dip that
looks, in the light curve alone, exactly like a planet on the target. The
target-pixel file shows where the light went missing:

1. For every transit with data inside it and on both sides, the difference image
   is the per-pixel median of the flanks (0.75-2 transit durations from
   mid-transit, both sides averaged) minus the median of the central 70 % of the
   transit. It is bright where the flux dropped. The difference images of a
   sector are averaged.
2. Its noise is the cadence-to-cadence scatter of each pixel, carried through the
   medians and scaled by one factor measured on the transits' own difference
   images (their scatter about the mean), or, with fewer than four transits, on
   difference images made at phases away from the transit and phase 0.5, so that
   slow systematics count too without making the noise map itself noisy.
3. A model of the TESS pixel response function (PRF) plus a constant is fitted
   to the mean difference image within 4 pixels of the target, started from the
   target, from the most significant pixel and from each catalogued star that
   could cause the dip; the best fit wins. Its position is where the dip is. Its
   uncertainty is the larger of the fit's and that from resampling the transits.
4. Each sector's position becomes an offset from the target's catalogue position
   on the sky (east, north), and the sectors are averaged with their
   covariances. A systematic floor (the PRF and the stamp's astrometry are good
   to about a tenth of a pixel) is added before the offset is compared with its
   uncertainty. The result is a Gaussian-equivalent significance.

The test fails when the target is excluded at ``centroid_sigma``, and names the
catalogued star at the dip's position if one is bright enough to cause it. A
pass means only that the dip is consistent with the target to within the
uncertainty, which the message states: blends closer than that stay possible.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from scipy.optimize import least_squares
from scipy.special import log_ndtr, ndtri_exp

from .lightcurve import LightCurve
from .pixels import Neighbour, PixelData, PixelSource, PRFModel, sky_offset
from .plotting import (
    AXIS,
    BLUE,
    INK,
    INK_MUTED,
    INK_SECONDARY,
    ORANGE,
    new_figure,
    save_figure,
    style,
)
from .utils import epoch_index, fold

log = logging.getLogger(__name__)

#: Half-width, in pixels, of the region around the target that the PRF is fitted in.
FIT_REGION_PX = 4.5
#: chi-square of 2 degrees of freedom at the 3-sigma (Gaussian two-sided) level.
_CHI2_3SIGMA_2DOF = 11.829
#: Blue (flux rose) through a light neutral to orange (flux dropped).
_DIVERGING = LinearSegmentedColormap.from_list("th_diverging", [BLUE, "#efeee8", ORANGE])


@dataclass
class SectorCentroid:
    """Where the dip is in one sector's target pixels."""

    sector: int
    n_transits: int
    noise_from: str
    noise_scale: float
    snr: float  # of the fitted PRF amplitude
    chi2_reduced: float
    x: float  # fitted position of the dip in the stamp (column, row)
    y: float
    cov_px: np.ndarray  # 2 x 2
    target_x: float
    target_y: float
    offset: np.ndarray  # (east, north) arcsec from the target
    cov: np.ndarray  # 2 x 2, arcsec^2, statistical only
    pixels: PixelData = field(repr=False)
    diff: np.ndarray = field(repr=False)
    diff_err: np.ndarray = field(repr=False)
    oot: np.ndarray = field(repr=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "sector": self.sector,
            "n_transits": self.n_transits,
            "noise_from": self.noise_from,
            "noise_scale": self.noise_scale,
            "snr": self.snr,
            "chi2_reduced": self.chi2_reduced,
            "position_px": [self.x, self.y],
            "target_px": [self.target_x, self.target_y],
            "offset_arcsec": [float(v) for v in self.offset],
            "offset_err_arcsec": [float(v) for v in np.sqrt(np.diag(self.cov))],
        }


@dataclass
class CentroidMeasurement:
    """The dip's position, combined over sectors, and the stars around the target."""

    sectors: list[SectorCentroid]
    skipped: list[dict[str, Any]]
    offset: np.ndarray | None = None  # (east, north) arcsec
    cov_stat: np.ndarray | None = None
    cov: np.ndarray | None = None  # with the systematic floor
    significance: float | None = None
    floor_arcsec: float = 0.0
    neighbours: list[dict[str, Any]] | None = None
    note: str | None = None

    @property
    def separation(self) -> float | None:
        return None if self.offset is None else float(np.hypot(*self.offset))


# --------------------------------------------------------------------------- images
def _windows(time: np.ndarray, tc: float, duration: float) -> tuple[np.ndarray, ...]:
    dt = time - tc
    inside = np.abs(dt) < 0.35 * duration
    before = (dt < -0.75 * duration) & (dt > -2.0 * duration)
    after = (dt > 0.75 * duration) & (dt < 2.0 * duration)
    return inside, before, after


def epoch_images(
    pixels: PixelData,
    period: float,
    t0: float,
    duration: float,
    phase: float = 0.0,
    epochs: set[int] | None = None,
) -> list[tuple[float, np.ndarray, np.ndarray]]:
    """(mid-time, difference image, out-of-transit image) of every covered transit.

    ``phase`` shifts the ephemeris (null images at other phases use the same code);
    ``epochs``, if given, limits the transits to those numbers.
    """
    time, flux = pixels.time, pixels.flux
    if time.size < 10:
        return []
    cadence = float(np.median(np.diff(time)))
    n_in = 0.7 * duration / cadence
    n_side = 1.25 * duration / cadence
    ref = t0 + phase * period
    out = []
    for epoch in np.unique(np.round((time - ref) / period)):
        if epochs is not None and int(epoch) not in epochs:
            continue
        tc = ref + epoch * period
        near = np.abs(time - tc) < 2.0 * duration
        if not near.any():
            continue
        inside, before, after = _windows(time[near], tc, duration)
        if inside.sum() < 0.5 * n_in or before.sum() < 0.3 * n_side or after.sum() < 0.3 * n_side:
            continue
        stack = flux[near]
        img_in = np.nanmedian(stack[inside], axis=0)
        img_out = 0.5 * (np.nanmedian(stack[before], axis=0) + np.nanmedian(stack[after], axis=0))
        out.append((float(tc), img_out - img_in, img_out))
    return out


def white_noise_map(pixels: PixelData, duration: float) -> np.ndarray:
    """Per-pixel white noise of one transit's difference image.

    The cadence-to-cadence scatter of each pixel, carried through the median of
    the in-transit window and the mean of the two flank medians.
    """
    step = np.diff(pixels.flux, axis=0)
    scatter = 1.4826 * np.nanmedian(np.abs(step), axis=0) / math.sqrt(2.0)
    cadence = float(np.median(np.diff(pixels.time)))
    n_in = max(0.7 * duration / cadence, 1.0)
    n_side = max(1.25 * duration / cadence, 1.0)
    median_var = math.pi / 2  # variance of a median relative to a mean
    return scatter * np.sqrt(median_var / n_in + 0.25 * 2 * median_var / n_side)


def _noise_scale(
    diffs: np.ndarray,
    white: np.ndarray,
    region: np.ndarray,
    pixels: PixelData,
    period: float,
    t0: float,
    duration: float,
) -> tuple[float, str]:
    """Factor by which the white-noise map underestimates the real scatter."""
    n = len(diffs)
    if n >= 4:
        resid = (diffs - diffs.mean(axis=0)) / white * math.sqrt(n / (n - 1))
        vals = resid[:, region]
        source = f"the scatter of the {n} transits"
    else:
        margin = 2.5 * duration / period
        phases = [
            p
            for p in np.arange(0.05, 0.96, 0.05)
            if min(p, 1 - p) > margin and abs(p - 0.5) > margin
        ]
        nulls = [d for ph in phases for (_, d, _) in epoch_images(pixels, period, t0, duration, ph)]
        if len(nulls) < 8:
            return 1.5, "white noise, scaled by 1.5 (too few transits and null images)"
        vals = (np.array(nulls) / white)[:, region]
        vals = vals - np.nanmedian(vals)
        source = f"{len(nulls)} null images at other phases"
    scale = 1.4826 * float(np.nanmedian(np.abs(vals)))
    return max(scale, 1.0), source


# --------------------------------------------------------------------------- fitting
def fit_prf(
    image: np.ndarray,
    sigma: np.ndarray,
    prf: PRFModel,
    start: tuple[float, float],
    region: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Least-squares fit of amplitude * PRF(x, y) + constant within ``region``.

    Returns the parameters (amplitude, x, y, constant), their covariance (scaled
    up by the reduced chi-square when it exceeds one) and the reduced chi-square.
    """
    ok = region & np.isfinite(image) & np.isfinite(sigma) & (sigma > 0)
    ys, xs = np.nonzero(region)
    # the amplitude cannot be negative: a dip is being located, not a brightening
    lo = [0.0, xs.min() - 0.5, ys.min() - 0.5, -np.inf]
    hi = [np.inf, xs.max() + 0.5, ys.max() + 0.5, np.inf]
    x0 = float(np.clip(start[0], lo[1] + 1e-3, hi[1] - 1e-3))
    y0 = float(np.clip(start[1], lo[2] + 1e-3, hi[2] - 1e-3))

    def resid(p: np.ndarray) -> np.ndarray:
        amp, x, y, const = p
        return ((amp * prf.model(x, y, image.shape) + const - image) / sigma)[ok]

    total = float(np.nansum(np.where(ok, image, 0.0)))
    scale = float(np.nanmax(np.where(ok, np.abs(image), 0.0))) or 1.0
    guess = [max(total, 1e-3 * scale), x0, y0, 0.0]
    res = least_squares(resid, guess, bounds=(lo, hi))
    dof = max(int(ok.sum()) - 4, 1)
    chi2r = float(np.sum(res.fun**2) / dof)
    try:
        cov = np.linalg.inv(res.jac.T @ res.jac) * max(1.0, chi2r)
    except np.linalg.LinAlgError:
        cov = np.full((4, 4), np.nan)
    return res.x, cov, chi2r


def measure_sector(
    pixels: PixelData,
    prf: PRFModel,
    period: float,
    t0: float,
    duration: float,
    hosts: list[tuple[float, float]] = (),
    n_bootstrap: int = 50,
    allowed: set[int] | None = None,
) -> SectorCentroid | str:
    """Locate the dip in one sector's pixels, or say why it cannot be done.

    ``allowed`` limits the transits to these epoch numbers (those the light-curve
    tests use, so that a transit left out there is left out here too).
    """
    epochs = epoch_images(pixels, period, t0, duration, epochs=allowed)
    if not epochs:
        return "no transit with data inside it and on both sides"
    tx, ty = pixels.target_pixel()
    ny, nx = pixels.shape
    yy, xx = np.mgrid[0:ny, 0:nx]
    region = (np.abs(xx - tx) <= FIT_REGION_PX) & (np.abs(yy - ty) <= FIT_REGION_PX)
    if region.sum() < 9:
        return "the target is at the edge of the stamp"
    diffs = np.array([d for _, d, _ in epochs])
    white = white_noise_map(pixels, duration)
    white = np.where(np.isfinite(white) & (white > 0), white, np.nan)
    scale, noise_from = _noise_scale(diffs, white, region, pixels, period, t0, duration)
    mean = np.nanmean(diffs, axis=0)
    err = scale * white / math.sqrt(len(diffs))
    oot = np.nanmean(np.array([o for _, _, o in epochs]), axis=0)

    snr_map = np.where(region & np.isfinite(mean / err), mean / err, -np.inf)
    peak = np.unravel_index(int(np.argmax(snr_map)), mean.shape)
    starts = [(tx, ty), (float(peak[1]), float(peak[0]))]
    starts += [
        (hx, hy)
        for hx, hy in hosts
        if abs(hx - tx) <= FIT_REGION_PX and abs(hy - ty) <= FIT_REGION_PX
    ]
    best = None
    for start in starts[:8]:
        fit = fit_prf(mean, err, prf, start, region)
        if best is None or fit[2] < best[2]:
            best = fit
    params, cov, chi2r = best
    amp_err = math.sqrt(cov[0, 0]) if np.isfinite(cov[0, 0]) and cov[0, 0] > 0 else np.inf
    snr = float(params[0] / amp_err)
    cov_px = cov[1:3, 1:3]
    if len(epochs) >= 3 and n_bootstrap > 0:
        rng = np.random.default_rng(pixels.sector)
        positions = []
        for _ in range(n_bootstrap):
            pick = rng.integers(0, len(diffs), len(diffs))
            sample = np.nanmean(diffs[pick], axis=0)
            p_b, _, _ = fit_prf(sample, err, prf, (params[1], params[2]), region)
            positions.append(p_b[1:3])
        cov_boot = np.cov(np.array(positions).T)
        if np.trace(cov_boot) > np.trace(cov_px):
            cov_px = cov_boot
    x, y = float(params[1]), float(params[2])
    jac = pixels.sky_jacobian(x, y)
    east, north = pixels.sky_offset(x, y)
    return SectorCentroid(
        sector=pixels.sector,
        n_transits=len(epochs),
        noise_from=noise_from,
        noise_scale=float(scale),
        snr=snr,
        chi2_reduced=chi2r,
        x=x,
        y=y,
        cov_px=cov_px,
        target_x=tx,
        target_y=ty,
        offset=np.array([east, north]),
        cov=jac @ cov_px @ jac.T,
        pixels=pixels,
        diff=mean,
        diff_err=err,
        oot=oot,
    )


# --------------------------------------------------------------------------- combining
def significance(offset: np.ndarray, cov: np.ndarray) -> float:
    """Gaussian-equivalent (two-sided) significance of a 2-D offset from zero."""
    d2 = float(offset @ np.linalg.solve(cov, offset))
    # chi-square with 2 degrees of freedom: tail probability exp(-d2 / 2)
    return float(-ndtri_exp(-0.5 * d2 - math.log(2.0)))


def _chi2_2dof(sigma: float) -> float:
    """chi-square (2 dof) whose tail probability matches a two-sided ``sigma``."""
    return -2.0 * (math.log(2.0) + float(log_ndtr(-sigma)))


def combine(
    sectors: list[SectorCentroid], floor_arcsec: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Covariance-weighted mean offset, its statistical and total covariance."""
    inv = [np.linalg.inv(s.cov) for s in sectors]
    info = np.sum(inv, axis=0)
    cov_stat = np.linalg.inv(info)
    mean = cov_stat @ np.sum([w @ s.offset for w, s in zip(inv, sectors, strict=True)], axis=0)
    cov = cov_stat + floor_arcsec**2 * np.eye(2)
    return mean, cov_stat, cov


def _sectors_by_transit_data(
    lc: LightCurve, period: float, t0: float, duration: float
) -> list[int]:
    """Sectors ordered by how many in-transit points of this signal they hold."""
    if lc.sector is None:
        return []
    inside = np.abs(fold(lc.time, period, t0)) < 0.35 * duration
    counts = {
        int(s): int(np.count_nonzero(inside & (lc.sector == s))) for s in np.unique(lc.sector)
    }
    return [s for s, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])) if c > 0]


def measure_centroid(
    source: PixelSource,
    lc: LightCurve,
    period: float,
    t0: float,
    duration: float,
    depth: float | None,
    floor_arcsec: float,
    min_snr: float,
    max_sectors: int,
) -> CentroidMeasurement:
    """Measure the dip's position in up to ``max_sectors`` sectors and combine them.

    Sectors are taken in order of how much in-transit data of this signal the
    light curve ``lc`` holds, and only transits with data in ``lc`` are used.
    """
    order = _sectors_by_transit_data(lc, period, t0, duration)
    inside = np.abs(fold(lc.time, period, t0)) < 0.35 * duration
    allowed = {int(e) for e in epoch_index(lc.time[inside], period, t0)}
    skipped: list[dict[str, Any]] = []
    measured: list[SectorCentroid] = []
    neighbours: list[Neighbour] | None = None
    target: PixelData | None = None
    for sector in order[: 2 * max_sectors]:
        if len(measured) >= max_sectors:
            break
        pixels = source.get(sector)
        if pixels is None:
            skipped.append({"sector": sector, "reason": source.error(sector) or "no pixels"})
            continue
        target = target or pixels
        if neighbours is None:
            neighbours = source.neighbours(pixels.ra, pixels.dec)
        prf = source.prf(pixels)
        if prf is None:
            skipped.append({"sector": sector, "reason": source.error(sector) or "no PRF model"})
            continue
        hosts = [
            pixels.world_to_pixel(*n.radec_at(pixels.epoch))
            for n in (neighbours or [])
            if _could_host(n, pixels.tmag, depth) and _separation(n, pixels) > 1.0
        ]
        result = measure_sector(pixels, prf, period, t0, duration, hosts, allowed=allowed)
        if isinstance(result, str):
            skipped.append({"sector": sector, "reason": result})
        elif not result.snr >= min_snr:
            skipped.append(
                {
                    "sector": sector,
                    "reason": f"dip not detected in the pixels (S/N {result.snr:.1f})",
                }
            )
        elif not (np.all(np.isfinite(result.cov)) and np.linalg.det(result.cov) > 0):
            skipped.append({"sector": sector, "reason": "the dip's position is undetermined"})
        else:
            measured.append(result)
    out = CentroidMeasurement(measured, skipped, floor_arcsec=floor_arcsec)
    if not measured:
        if not order:
            out.note = "no sector with in-transit data"
        elif skipped and all("S/N" in s["reason"] for s in skipped):
            best = max(float(s["reason"].split("S/N ")[1].rstrip(")")) for s in skipped)
            out.note = f"dip not detected in the target pixels (best S/N {best:.1f})"
        else:
            reasons = sorted({s["reason"] for s in skipped})
            out.note = reasons[0] if len(reasons) == 1 else "; ".join(reasons[:2])
        return out
    out.offset, out.cov_stat, out.cov = combine(measured, floor_arcsec)
    out.significance = significance(out.offset, out.cov)
    if neighbours is not None and target is not None:
        out.neighbours = _describe_neighbours(neighbours, target, depth, out.offset, out.cov)
    return out


def _offset(n: Neighbour, pixels: PixelData) -> tuple[float, float]:
    """(east, north) arcsec of a neighbour from the target, both at the sector's epoch."""
    return sky_offset(*pixels.target_radec(), *n.radec_at(pixels.epoch))


def _separation(n: Neighbour, pixels: PixelData) -> float:
    return float(np.hypot(*_offset(n, pixels)))


def _could_host(n: Neighbour, tmag: float | None, depth: float | None) -> bool:
    """Bright enough to cause the dip even if it were totally eclipsed."""
    if tmag is None or depth is None or depth <= 0:
        return True
    return 10 ** (-0.4 * (n.tmag - tmag)) >= depth


def _describe_neighbours(
    neighbours: list[Neighbour],
    target: PixelData,
    depth: float | None,
    offset: np.ndarray,
    cov: np.ndarray,
    radius_arcsec: float = 120.0,
) -> list[dict[str, Any]]:
    out = []
    for n in neighbours:
        east, north = _offset(n, target)
        sep = float(np.hypot(east, north))
        if sep < 1.0 or sep > radius_arcsec:
            continue  # the target itself, or too far to matter
        rel = np.array([east, north]) - offset
        out.append(
            {
                "tic_id": n.tic_id,
                "tmag": n.tmag,
                "separation_arcsec": sep,
                "offset_arcsec": [east, north],
                "could_host": _could_host(n, target.tmag, depth),
                "distance_from_dip_arcsec": float(np.hypot(*rel)),
                "excluded_sigma": significance(rel, cov),
            }
        )
    out.sort(key=lambda d: d["distance_from_dip_arcsec"])
    return out


# --------------------------------------------------------------------------- the test
def centroid_test(measurement: CentroidMeasurement, sigma_threshold: float) -> Any:
    """Turn a :class:`CentroidMeasurement` into a vetting test result."""
    from .vet import FAIL, NA, PASS, TestResult

    if not measurement.sectors or measurement.offset is None:
        return TestResult(
            "centroid",
            NA,
            float("nan"),
            measurement.note or "no usable target pixels",
            {"skipped": measurement.skipped},
        )
    sig = float(measurement.significance)
    sep = measurement.separation
    n = len(measurement.sectors)
    where = f"{sep:.1f}″ from the target ({sig:.1f}σ, {n} sector{'s' if n > 1 else ''})"
    # radius around the dip within which a star cannot be excluded at the threshold
    radius = math.sqrt(
        _chi2_2dof(sigma_threshold) * float(np.max(np.linalg.eigvalsh(measurement.cov)))
    )
    hosts = [d for d in measurement.neighbours or [] if d["could_host"]]
    if sig >= sigma_threshold:
        status = FAIL
        on = [d for d in hosts if d["excluded_sigma"] < sigma_threshold]
        if on:
            d = on[0]
            message = (
                f"the dip is {where}, at TIC {d['tic_id']} (Tmag {d['tmag']:.1f}, "
                f"{d['separation_arcsec']:.0f}″ from the target), which is bright enough "
                "to cause it"
            )
        elif measurement.neighbours is None:
            message = f"the dip is {where}"
        else:
            message = f"the dip is {where}; no catalogued star bright enough to cause it lies there"
    else:
        status = PASS
        close = [d for d in hosts if d["excluded_sigma"] < sigma_threshold]
        message = f"the dip is {where}; stars within {radius:.0f}″ of it cannot be excluded"
        if measurement.neighbours is None:
            message += " (stars around the target could not be looked up)"
        elif close:
            names = ", ".join(
                f"TIC {d['tic_id']} (Tmag {d['tmag']:.1f}, {d['separation_arcsec']:.0f}″)"
                for d in close[:2]
            )
            more = f" and {len(close) - 2} more" if len(close) > 2 else ""
            message += f": {names}{more} could cause it"
        else:
            message += ", and no catalogued star there is bright enough to cause it"
    details = {
        "offset_arcsec": [float(v) for v in measurement.offset],
        "separation_arcsec": sep,
        "offset_cov_arcsec2": measurement.cov.tolist(),
        "floor_arcsec": measurement.floor_arcsec,
        "exclusion_radius_arcsec": radius,
        "sectors": [s.as_dict() for s in measurement.sectors],
        "skipped": measurement.skipped,
        "neighbours": (measurement.neighbours or [])[:10],
    }
    return TestResult("centroid", status, sig, message, details)


# --------------------------------------------------------------------------- figure
def plot_centroid(
    measurement: CentroidMeasurement, test: Any, path: str | Path, title: str = ""
) -> Path | None:
    """Out-of-transit image, difference image and the dip's position on the sky.

    Catalogued stars within 5 magnitudes of the target are drawn, filled if they
    are bright enough to cause the dip even when totally eclipsed.
    """
    if not measurement.sectors or measurement.offset is None:
        return None
    best = max(measurement.sectors, key=lambda s: s.snr)
    pix = best.pixels
    ra_t, dec_t = pix.target_radec()
    shown = [
        d for d in measurement.neighbours or [] if pix.tmag is None or d["tmag"] <= pix.tmag + 5.0
    ]
    in_stamp = []
    for d in shown:
        ra = ra_t + d["offset_arcsec"][0] / 3600 / math.cos(math.radians(dec_t))
        dec = dec_t + d["offset_arcsec"][1] / 3600
        in_stamp.append((pix.world_to_pixel(ra, dec), d))

    def size(tmag: float) -> float:
        return float(np.clip(12.0 - 1.6 * (tmag - (pix.tmag or tmag)), 3.0, 12.0))

    with style():
        fig, axes = new_figure(1, 3, figsize=(14, 5.6))
        fig.get_layout_engine().set(rect=(0, 0.1, 1, 0.9))
        ax_img, ax_diff, ax_sky = axes[0]
        ny, nx = pix.shape

        def mark(ax: Any) -> None:
            for y, x in zip(*np.nonzero(pix.aperture), strict=True):
                ax.add_patch(_square(x, y, edge=AXIS, lw=1.0))
            for (x, y), d in in_stamp:
                if -0.5 < x < nx - 0.5 and -0.5 < y < ny - 0.5:
                    ax.plot(
                        x,
                        y,
                        "o",
                        ms=size(d["tmag"]),
                        mfc=ORANGE if d["could_host"] else "none",
                        mec=ORANGE,
                        mew=1.2,
                    )
            ax.plot(best.target_x, best.target_y, "*", ms=15, mfc="white", mec=INK, mew=1.0)
            ax.set_xlim(-0.5, nx - 0.5)
            ax.set_ylim(-0.5, ny - 0.5)
            ax.set_xlabel("column (pixels)")
            ax.set_ylabel("row (pixels)")
            ax.grid(False)

        img = np.where(best.oot > 0, best.oot, np.nan)
        ax_img.imshow(np.log10(img), origin="lower", cmap="Greys_r", interpolation="nearest")
        mark(ax_img)
        ax_img.set_title(
            f"out of transit, sector {best.sector}", loc="left", fontsize=10, color=INK
        )

        snr = best.diff / best.diff_err
        lim = max(3.0, float(np.nanpercentile(np.abs(snr), 99)))
        ax_diff.imshow(
            snr, origin="lower", cmap=_DIVERGING, vmin=-lim, vmax=lim, interpolation="nearest"
        )
        mark(ax_diff)
        floor_px = measurement.floor_arcsec / 21.0
        _ellipse(ax_diff, best.x, best.y, best.cov_px + floor_px**2 * np.eye(2), INK)
        ax_diff.plot(best.x, best.y, "x", ms=10, mew=2, color=INK)
        ax_diff.set_title(
            "difference (out − in) / noise: where the flux dropped",
            loc="left",
            fontsize=10,
            color=INK,
        )

        offs = np.array([s.offset for s in measurement.sectors])
        errs = np.array([np.sqrt(np.diag(s.cov)) for s in measurement.sectors])
        reach = max(25.0, 1.5 * float(np.max(np.abs(offs))) + 10.0)
        nearby = [
            d
            for d in shown
            if abs(d["offset_arcsec"][0]) < reach and abs(d["offset_arcsec"][1]) < reach
        ]
        for d in nearby:
            ax_sky.plot(
                *d["offset_arcsec"],
                "o",
                ms=size(d["tmag"]),
                mfc=ORANGE if d["could_host"] else "none",
                mec=ORANGE,
                mew=1.2,
            )
        for d in sorted(nearby, key=lambda d: d["distance_from_dip_arcsec"])[:6]:
            ax_sky.annotate(
                f"{d['tmag']:.1f}",
                d["offset_arcsec"],
                textcoords="offset points",
                xytext=(6, 5),
                fontsize=7.5,
                color=INK_SECONDARY,
            )
        ax_sky.errorbar(
            offs[:, 0],
            offs[:, 1],
            xerr=errs[:, 0],
            yerr=errs[:, 1],
            fmt="o",
            ms=4,
            color=BLUE,
            lw=1,
            label="each sector (1σ, statistical)",
        )
        _ellipse(ax_sky, measurement.offset[0], measurement.offset[1], measurement.cov, INK)
        ax_sky.plot(*measurement.offset, "x", ms=10, mew=2, color=INK, label="combined (3σ)")
        ax_sky.plot(0, 0, "*", ms=15, mfc="white", mec=INK, mew=1.0)
        ax_sky.set_xlim(reach, -reach)  # east to the left, as on the sky
        ax_sky.set_ylim(-reach, reach)
        ax_sky.set_aspect("equal")
        ax_sky.set_xlabel("east of target (″)")
        ax_sky.set_ylabel("north of target (″)")
        ax_sky.legend(loc="lower left", fontsize=8)
        ax_sky.set_title("where the dip is, on the sky", loc="left", fontsize=10, color=INK)

        fig.text(
            0.01,
            0.055,
            "★ target    ● catalogued star bright enough to cause the dip    "
            "○ fainter catalogued star (stars more than 5 magnitudes fainter than the "
            "target are not shown; labels give TESS magnitudes)",
            fontsize=8,
            color=INK_MUTED,
        )
        fig.text(0.01, 0.015, f"[{test.status}] {test.message}", fontsize=9, color=INK_SECONDARY)
        fig.suptitle(
            f"{title}  —  centroid: {test.status.upper()}" if title else f"centroid: {test.status}",
            x=0.01,
            ha="left",
            fontsize=12,
            fontweight="bold",
        )
        return save_figure(fig, path)


def _square(x: float, y: float, edge: str, lw: float) -> Any:
    from matplotlib.patches import Rectangle

    return Rectangle((x - 0.5, y - 0.5), 1, 1, fill=False, edgecolor=edge, lw=lw)


def _ellipse(ax: Any, x: float, y: float, cov: np.ndarray, color: str) -> None:
    """3-sigma (2-D) confidence ellipse of a position with covariance ``cov``."""
    from matplotlib.patches import Ellipse

    vals, vecs = np.linalg.eigh(cov)
    vals = np.clip(vals, 0, None)
    angle = math.degrees(math.atan2(vecs[1, 1], vecs[0, 1]))
    k = math.sqrt(_CHI2_3SIGMA_2DOF)
    ax.add_patch(
        Ellipse(
            (x, y),
            2 * k * math.sqrt(vals[1]),
            2 * k * math.sqrt(vals[0]),
            angle=angle,
            fill=False,
            edgecolor=color,
            lw=1.2,
            ls="--",
        )
    )
