"""False-positive vetting diagnostics.

Eclipsing binaries (EBs) -- on the target or blended with it -- are the main
astrophysical impostors of transiting planets. Each test below looks for a
specific EB signature; all but the centroid test use the light curve alone.

``odd_even``
    An EB with two similar eclipses per orbit is found by BLS at *half* its
    true period; its "odd" and "even" transits are then different eclipses and
    generally have different depths. We fit the amplitude of the transit shape
    separately to odd and even epochs and compare them.

``secondary``
    A self-luminous companion is eclipsed half an orbit after the primary event
    (for circular orbits). We measure the flux deficit in a box of one transit
    duration centred on phase 0.5, and also scan all phases for eccentric
    orbits. A significant secondary is only damning if it is deeper than a
    planet could produce: we compare it with the largest plausible planetary
    occultation (geometric albedo 1 plus a zero-albedo, no-redistribution
    dayside emitting as a blackbody in the TESS band).

``shape``
    A planet much smaller than its star gives a flat-bottomed "U" transit with
    short ingress/egress; grazing EBs give "V" shapes. We fit a trapezoid and
    report the ingress+egress fraction of the total duration (0 = box, 1 = V),
    and the posterior probability that the fitted geometry is grazing.

``density``
    For a circular orbit, the transit shape fixes a/R*, which with the period
    gives the mean stellar density (Seager & Mallen-Ornelas 2003). A strong
    mismatch with the catalogue density points to a blend, a wrong host star,
    or an eccentric orbit.

``radius`` (supplementary)
    A companion larger than ~2.5 Jupiter radii is not a planet.

``coverage``
    A transit needs data inside it and on both sides. Dips at the very start or
    end of a data segment (after a gap, at an orbit or sector boundary) are
    common instrumental artefacts; a signal none of whose transits is fully
    covered fails.

``momentum_dumps``
    Every few days TESS fires its thrusters to unload its reaction wheels, and
    the jolt to the pointing can move light between neighbouring stars'
    apertures for an hour or so. Dips made that way recur at dump times, and a
    search can line several of them up at a period. A signal fails when its
    transits at dumps carry the dip and the others barely show it, or when every
    transit falls at a dump against the odds. Light curves that do not record
    the dump times skip the test.

``centroid``
    A TESS pixel is 21 arcsec across, so an eclipsing binary a few pixels away
    can dim the target's aperture. The target-pixel files show where the flux
    dropped: a model of the TESS pixel response is fitted to the in-transit
    difference images, and a dip significantly offset from the target fails
    (see :mod:`transit_hunter.centroid`).

``rotation`` (warning only)
    Detrending leaves a residual of starspot modulation, and on noise-only
    simulations of spotted stars the search's false alarms fall at the rotation
    period or half of it. The rotation period is measured with a Lomb-Scargle
    periodogram of the un-detrended light curve (transits masked), and a
    candidate at half, once, or twice that period gets a warning. Planets can
    orbit there too, so this is not a failure.

Uncertainties include a red-noise factor ``beta`` (the ratio of the observed
scatter of binned out-of-transit residuals to the white-noise expectation).
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np
from astropy.timeseries import LombScargle
from scipy.optimize import least_squares, minimize_scalar
from scipy.special import log_ndtr, logsumexp, ndtri_exp
from scipy.stats import chi2 as chi2_dist

from .catalog import StellarParams
from .centroid import CentroidMeasurement, centroid_test, measure_centroid
from .lightcurve import LightCurve
from .models import BatmanModel, TransitParams
from .pixels import PixelSource
from .plotting import (
    AXIS,
    BLUE,
    INK,
    INK_MUTED,
    INK_SECONDARY,
    ORANGE,
    STATUS_CRITICAL,
    STATUS_GOOD,
    STATUS_WARNING,
    new_figure,
    save_figure,
    style,
)
from .utils import (
    R_JUP,
    R_SUN,
    bin_timeseries,
    binned_rms,
    epoch_index,
    fold,
    robust_std,
    segment_bounds,
)

PASS, WARN, FAIL, NA = "pass", "warn", "fail", "n/a"

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class VetConfig:
    """Decision thresholds (sigma values are Gaussian-equivalent significances)."""

    odd_even_sigma: float = 3.0
    secondary_sigma: float = 3.0
    secondary_scan_sigma: float = 5.0  # stricter: the phase scan tries many phases
    secondary_planet_factor: float = 2.0  # "too deep" = this many times the planetary maximum
    v_shape_warn: float = 0.8
    density_sigma: float = 3.0
    density_factor_fail: float = 5.0
    max_planet_radius_rjup: float = 2.5
    rotation_tolerance: float = 0.05  # fractional period mismatch counted as "at" P_rot
    coverage_min: float = 0.75  # share of a transit's cadences needed to count it as covered
    dump_margin_hours: float = 1.0  # a transit this close to a momentum dump is "at" it
    dump_sigma: float = 3.0  # transits at dumps this much deeper stand out; fail if the rest
    # show no dip at this significance
    dump_chance: float = 0.01  # every transit at a dump fails when chance gives that this rarely
    rotation_min_power: float = 0.1  # Lomb-Scargle power needed to trust a rotation period
    odd_even_min_per_parity: int = 3  # transits per parity needed to measure their scatter
    bad_transit_sigma: float = 5.0  # a transit this far from the others' depth is dropped
    bad_transit_min_count: int = 6  # transits needed before any is judged against the rest
    bad_transit_max_fraction: float = 0.1  # at most this share of transits is dropped
    centroid_sigma: float = 3.0  # a dip this far from the target fails
    centroid_floor_arcsec: float = 2.5  # systematic error of a sector's dip position
    centroid_min_snr: float = 4.0  # dip S/N in the pixels needed to locate it
    centroid_max_sectors: int = 4  # sectors of target pixels used per candidate


@dataclass
class TestResult:
    __test__ = False  # not a pytest test class

    name: str
    status: str  # pass / warn / fail / n/a
    statistic: float
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class VettingReport:
    tests: list[TestResult]
    verdict: str
    reasons: list[str]
    centroid: CentroidMeasurement | None = None  # for the figure; not in as_dict()

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "reasons": self.reasons,
            "tests": [asdict(t) for t in self.tests],
        }

    def test(self, name: str) -> TestResult:
        return next(t for t in self.tests if t.name == name)


# --------------------------------------------------------------------------- helpers
def trapezoid(
    t: np.ndarray, tc: float, depth: float, t14: float, ingress_fraction: float
) -> np.ndarray:
    """Trapezoidal transit: total duration ``t14``, ingress+egress = ``ingress_fraction * t14``."""
    x = np.abs(np.asarray(t, dtype=float) - tc)
    half = 0.5 * t14
    tau = max(0.5 * ingress_fraction * t14, 1e-9)  # duration of ingress alone
    flux = np.ones_like(x)
    flat = x <= half - tau
    ramp = (x > half - tau) & (x < half)
    flux[flat] = 1.0 - depth
    flux[ramp] = 1.0 - depth * (half - x[ramp]) / tau
    return flux


def noise_properties(
    lc: LightCurve, period: float, t0: float, duration: float
) -> tuple[float, float]:
    """Per-point scatter and red-noise factor beta from out-of-transit data.

    Points near phase 0 and phase 0.5 are excluded so that neither eclipse
    inflates the estimate. For a signal so long that nothing lies clear of both
    windows (a "transit" lasting a quarter of the orbit, which no planet around
    a normal star makes), only the transit itself is excluded, and failing that
    nothing.
    """
    phase = fold(lc.time, period, t0)
    phase_sec = fold(lc.time, period, t0 + 0.5 * period)
    oot = (np.abs(phase) > duration) & (np.abs(phase_sec) > duration)
    if oot.sum() < 100:
        oot = np.abs(phase) > 0.5 * duration
    if oot.sum() < 100:
        oot = np.ones(lc.time.size, dtype=bool)
    sigma = robust_std(lc.flux[oot])
    cadence = np.median(np.diff(lc.time))
    n_per_bin = max(duration / cadence, 1.0)
    binned = binned_rms(lc.time[oot], lc.flux[oot], duration)
    beta = binned / (sigma / math.sqrt(n_per_bin)) if sigma > 0 and np.isfinite(binned) else 1.0
    return float(sigma), float(max(beta, 1.0))


def _shape_template(
    lc: LightCurve, period: float, t0: float, duration: float, model: np.ndarray | None
) -> np.ndarray:
    """Transit shape normalised to unit depth: the fitted model if given, else a box."""
    if model is not None:
        s = 1.0 - np.asarray(model, dtype=float) / np.max(model)
        peak = s.max()
        return s / peak if peak > 0 else s
    return (np.abs(fold(lc.time, period, t0)) < 0.5 * duration).astype(float)


def _amplitude(y: np.ndarray, template: np.ndarray, sigma: float) -> tuple[float, float]:
    """Least-squares amplitude of ``template`` in ``y`` (equal weights)."""
    ss = float(np.sum(template**2))
    if ss <= 0:
        return float("nan"), float("nan")
    amp = float(np.sum(template * y) / ss)
    return amp, sigma / math.sqrt(ss)


# --------------------------------------------------------------------------- tests
def odd_even_test(
    lc: LightCurve,
    period: float,
    t0: float,
    duration: float,
    model: np.ndarray | None = None,
    config: VetConfig | None = None,
) -> TestResult:
    """Compare transit depths of odd and even epochs.

    Each transit is measured against its own surroundings: the reference level is
    the median of the out-of-transit points within 1.5 durations of it (the
    median of all out-of-transit data if it has fewer than five), so a
    detrending residual that shifts the flux around one transit does not
    masquerade as a change of depth. Each parity's depth is then the
    least-squares amplitude of the transit shape. Its uncertainty combines the
    per-point scatter, inflated by the red-noise factor beta, with that of the
    local reference levels.

    That uncertainty still ignores real transit-to-transit variation
    (instrumental systematics, spots), so at very high S/N a difference of a
    percent can look significant. When both parities have at least
    ``odd_even_min_per_parity`` transits, each parity's uncertainty is raised to
    at least the scatter of single-transit depths about their own parity's
    median, divided by the square root of their number. Taking the scatter
    within each parity keeps a binary's alternating depths from inflating it.
    """
    config = config or VetConfig()
    sigma, beta = noise_properties(lc, period, t0, duration)
    near = np.abs(fold(lc.time, period, t0)) < 1.5 * duration
    template = _shape_template(lc, period, t0, duration, model)
    baseline = np.median(lc.flux[~near]) if np.any(~near) else 1.0
    epochs = epoch_index(lc.time, period, t0)
    # Reference level of each transit and the variance it adds to each point.
    level = np.full(lc.time.size, baseline)
    level_var = np.zeros(lc.time.size)
    for epoch in np.unique(epochs[near]):
        window = near & (epochs == epoch)
        flank = window & (template <= 1e-6)
        if flank.sum() >= 5:
            level[window] = np.median(lc.flux[flank])
            level_var[window] = (1.2533 * sigma * beta) ** 2 / flank.sum()
    y = level - lc.flux
    single: dict[int, float] = {}  # depth of each transit with data in its core
    for epoch in np.unique(epochs[near & (template > 0.5)]):
        use = near & (epochs == epoch)
        if np.sum(use & (template > 0.5)) >= 3:
            amp, _ = _amplitude(y[use], template[use], sigma * beta)
            if np.isfinite(amp):
                single[int(epoch)] = amp
    results = {}
    for parity, sel in (("odd", epochs % 2 == 1), ("even", epochs % 2 == 0)):
        use = near & sel
        n_transits = int(np.unique(epochs[use & (template > 0.5)]).size)
        amp, err = _amplitude(y[use], template[use], sigma * beta)
        ss = float(np.sum(template[use] ** 2))
        if ss > 0 and np.isfinite(err):
            # One reference level per transit: its error is common to all the
            # transit's points, so it enters through the transit's summed template.
            level_term = sum(
                float(np.sum(template[use & (epochs == e)])) ** 2
                * float(level_var[use & (epochs == e)][0])
                for e in np.unique(epochs[use])
            )
            err = math.sqrt(err**2 + level_term / ss**2)
        results[parity] = {"depth": amp, "depth_err": err, "n_transits": n_transits}
    odd, even = results["odd"], results["even"]
    if min(odd["n_transits"], even["n_transits"]) < 1:
        return TestResult(
            "odd_even",
            NA,
            float("nan"),
            "need at least one odd and one even transit",
            results | {"beta": beta},
        )
    if not (np.isfinite(odd["depth_err"]) and np.isfinite(even["depth_err"])):
        return TestResult(
            "odd_even", NA, float("nan"), "the noise level could not be measured", results
        )
    scatter, floored = transit_scatter_floor(single, results, config)
    diff = odd["depth"] - even["depth"]
    err = math.hypot(odd["depth_err"], even["depth_err"])
    significance = abs(diff) / err
    status = FAIL if significance > config.odd_even_sigma else PASS
    message = (
        f"odd depth {odd['depth'] * 1e6:.0f}±{odd['depth_err'] * 1e6:.0f} ppm vs even "
        f"{even['depth'] * 1e6:.0f}±{even['depth_err'] * 1e6:.0f} ppm: "
        f"{significance:.1f}σ difference"
    )
    if floored:
        message += f" (uncertainties include the {scatter * 1e6:.0f} ppm scatter between transits)"
    return TestResult(
        "odd_even",
        status,
        significance,
        message,
        results
        | {
            "difference": diff,
            "difference_err": err,
            "beta": beta,
            "transit_scatter": scatter,
            "scatter_floor_applied": floored,
        },
    )


def transit_scatter_floor(
    single: dict[int, float], results: dict[str, dict[str, float]], config: VetConfig
) -> tuple[float | None, bool]:
    """Raise each parity's depth uncertainty to the scatter of its single transits.

    ``single`` maps epoch to single-transit depth; ``results`` holds each parity's
    ``depth_err`` and is updated in place. Returns the robust within-parity
    scatter (None if a parity has too few transits) and whether it raised an
    uncertainty.
    """
    groups = {
        parity: np.array([d for e, d in single.items() if e % 2 == remainder])
        for parity, remainder in (("odd", 1), ("even", 0))
    }
    if min(g.size for g in groups.values()) < config.odd_even_min_per_parity:
        return None, False
    deviations = np.concatenate([g - np.median(g) for g in groups.values()])
    scatter = 1.4826 * float(np.median(np.abs(deviations)))
    floored = False
    for parity, depths in groups.items():
        floor = scatter / math.sqrt(depths.size)
        if floor > results[parity]["depth_err"]:
            results[parity]["depth_err"] = floor
            floored = True
    return scatter, floored


def _box_depth(
    offset: np.ndarray, flux: np.ndarray, width: float, sigma: float, beta: float
) -> tuple[float, float, int]:
    """Deficit inside |offset| < width/2 relative to the flanking baseline."""
    inside = np.abs(offset) < 0.5 * width
    flank = (np.abs(offset) >= 0.5 * width) & (np.abs(offset) < 1.5 * width)
    n_in, n_out = int(inside.sum()), int(flank.sum())
    if n_in < 3 or n_out < 3:
        return float("nan"), float("nan"), n_in
    depth = float(np.mean(flux[flank]) - np.mean(flux[inside]))
    err = sigma * beta * math.sqrt(1.0 / n_in + 1.0 / n_out)
    return depth, err, n_in


def _leave_one_orbit_out(
    offset: np.ndarray, flux: np.ndarray, width: float, sigma: float, beta: float, orbit: np.ndarray
) -> tuple[float, int, int | None]:
    """S/N of a box dip after leaving out the orbit that contributes most to it.

    ``orbit`` numbers each point's orbit. A real eclipse repeats every orbit and
    stays significant without any one of them; a single instrumental dip does
    not. Returns the smallest leave-one-out S/N, the number of orbits with data
    inside the box, and the orbit whose removal hurts most. With data inside the
    box from fewer than two orbits the dip cannot be confirmed and the S/N is NaN.
    """
    inside = np.abs(offset) < 0.5 * width
    flank = (np.abs(offset) >= 0.5 * width) & (np.abs(offset) < 1.5 * width)
    orbits_in = np.unique(orbit[inside])
    if orbits_in.size < 2:
        return float("nan"), int(orbits_in.size), None
    labels, index = np.unique(orbit[inside | flank], return_inverse=True)
    region = flux[inside | flank]
    is_in = inside[inside | flank]
    n_in = np.bincount(index, weights=is_in.astype(float), minlength=labels.size)
    n_fl = np.bincount(index, weights=(~is_in).astype(float), minlength=labels.size)
    s_in = np.bincount(index, weights=np.where(is_in, region, 0.0), minlength=labels.size)
    s_fl = np.bincount(index, weights=np.where(is_in, 0.0, region), minlength=labels.size)
    rest_in, rest_fl = n_in.sum() - n_in, n_fl.sum() - n_fl
    ok = (rest_in >= 3) & (rest_fl >= 3)
    if not np.any(ok):
        return float("nan"), int(orbits_in.size), None
    depth = (s_fl.sum() - s_fl[ok]) / rest_fl[ok] - (s_in.sum() - s_in[ok]) / rest_in[ok]
    err = sigma * beta * np.sqrt(1.0 / rest_in[ok] + 1.0 / rest_fl[ok])
    snr = depth / err
    worst = int(np.argmin(snr))
    return float(snr[worst]), int(orbits_in.size), int(labels[ok][worst])


def _planck_band(temperature: float, lo: float = 600e-9, hi: float = 1000e-9) -> float:
    """Blackbody radiance integrated over a top-hat approximation of the TESS band."""
    h, c, k_b = 6.62607015e-34, 2.99792458e8, 1.380649e-23
    lam = np.linspace(lo, hi, 400)
    with np.errstate(over="ignore"):
        radiance = 2 * h * c**2 / lam**5 / np.expm1(h * c / (lam * k_b * temperature))
    return float(np.sum(radiance) * (lam[1] - lam[0]))


def max_planet_occultation(rp_rs: float, a_rs: float, teff: float | None) -> float:
    """Largest plausible occultation depth of a planet (fraction of stellar flux).

    Reflected light with geometric albedo 1, ``(Rp/a)^2``, plus thermal emission
    of a zero-albedo dayside without heat redistribution,
    ``T_day = Teff sqrt(R*/a) (2/3)^(1/4)``, radiating as a blackbody in the
    TESS band (600-1000 nm top-hat). Both choices are deliberately generous.
    """
    reflected = (rp_rs / a_rs) ** 2
    thermal = 0.0
    if teff:
        t_day = teff * math.sqrt(1.0 / a_rs) * (2.0 / 3.0) ** 0.25
        thermal = rp_rs**2 * _planck_band(t_day) / _planck_band(teff)
    return reflected + thermal


def secondary_eclipse_test(
    lc: LightCurve,
    period: float,
    t0: float,
    duration: float,
    rp_rs: float | None = None,
    a_rs: float | None = None,
    teff: float | None = None,
    config: VetConfig | None = None,
) -> TestResult:
    """Search for an occultation at phase 0.5 (and report the strongest dip at any phase).

    A dip counts only if it stays significant when the orbit contributing most to
    it is left out (see :func:`_leave_one_orbit_out`), so a single instrumental
    event cannot pass for an eclipse. Dips that fail this are reported in the
    message but do not affect the outcome.
    """
    config = config or VetConfig()
    sigma, beta = noise_properties(lc, period, t0, duration)
    offset = fold(lc.time, period, t0 + 0.5 * period)
    depth, err, n_in = _box_depth(offset, lc.flux, duration, sigma, beta)
    orbit = epoch_index(lc.time, period, t0 + 0.5 * period)
    loo_snr, n_orbits, _ = _leave_one_orbit_out(offset, lc.flux, duration, sigma, beta, orbit)
    details: dict[str, Any] = {
        "depth": depth,
        "depth_err": err,
        "n_points": n_in,
        "beta": beta,
        "n_orbits": n_orbits,
        "snr_without_strongest_orbit": loo_snr,
    }

    # Phase scan (eccentric orbits): exclude +/- 1.5 durations around the primary.
    phase_primary = fold(lc.time, period, t0)
    step = max(duration / 4.0, period / 2000.0)
    keep = np.abs(phase_primary) > 1.5 * duration
    scan = []
    for centre in np.arange(2.0 * duration, period - 2.0 * duration, step):
        off = fold(lc.time[keep], period, t0 + centre)
        d, e, _ = _box_depth(off, lc.flux[keep], duration, sigma, beta)
        if np.isfinite(d):
            scan.append((d / e, centre, d))
    # The strongest few distinct dips; the best one that survives leaving out an orbit wins.
    best = (float("-inf"), float("nan"), float("nan"))
    single_orbit_dips = []
    tried: list[float] = []
    for snr_c, centre, d in sorted(scan, reverse=True):
        if len(tried) == 5:
            break
        if any(abs(centre - c) < duration for c in tried):
            continue
        tried.append(centre)
        off = fold(lc.time[keep], period, t0 + centre)
        orb = epoch_index(lc.time[keep], period, t0 + centre)
        robust, _, _ = _leave_one_orbit_out(off, lc.flux[keep], duration, sigma, beta, orb)
        if np.isfinite(robust) and robust >= config.secondary_scan_sigma:
            if snr_c > best[0]:
                best = (snr_c, centre / period, d)
        elif snr_c >= config.secondary_scan_sigma:
            single_orbit_dips.append((centre / period, d, snr_c))
    details.update(
        {
            "scan_max_snr": best[0],
            "scan_phase": best[1],
            "scan_depth": best[2],
            "scan_single_orbit_dips": [
                {"phase": ph, "depth": d, "snr": sn} for ph, d, sn in single_orbit_dips
            ],
        }
    )
    note = ""
    if single_orbit_dips:
        ph, d, sn = max(single_orbit_dips, key=lambda x: x[2])
        note = (
            f"; a {d * 1e6:.0f} ppm dip at phase {ph:.2f} ({sn:.1f}σ) comes from a single orbit "
            "and is not counted"
        )

    if not np.isfinite(depth):
        return TestResult("secondary", NA, float("nan"), "no data near phase 0.5", details)
    if not (np.isfinite(err) and err > 0):
        return TestResult(
            "secondary", NA, float("nan"), "the noise level could not be measured", details
        )
    snr = depth / err
    decisive = snr  # the S/N the decision uses
    if snr >= config.secondary_sigma and not (
        np.isfinite(loo_snr) and loo_snr >= config.secondary_sigma
    ):
        # Significant only because of one orbit: an instrumental event, not an eclipse.
        note = "; the phase-0.5 dip comes from a single orbit and is not counted" + note
        decisive = loo_snr if np.isfinite(loo_snr) else 0.0
    limit = None
    if rp_rs is not None and a_rs is not None:
        limit = max_planet_occultation(rp_rs, a_rs, teff)
        details["max_planet_depth"] = limit
    measured = f"{depth * 1e6:.0f}±{err * 1e6:.0f} ppm, {snr:.1f}σ"
    scan_snr, scan_phase, scan_depth = best
    scan_significant = bool(np.isfinite(scan_snr) and scan_snr >= config.secondary_scan_sigma)
    if decisive < config.secondary_sigma:
        if (
            scan_significant
            and limit is not None
            and scan_depth > config.secondary_planet_factor * limit
        ):
            status = FAIL
            message = (
                f"no eclipse at phase 0.5 ({measured}), but a {scan_depth * 1e6:.0f} ppm dip "
                f"({scan_snr:.1f}σ) at phase {scan_phase:.2f}, deeper than any planetary "
                f"occultation (≤{limit * 1e6:.0f} ppm): eccentric eclipsing binary?{note}"
            )
        elif scan_significant:
            status = WARN
            message = (
                f"no eclipse at phase 0.5 ({measured}); strongest dip at phase "
                f"{scan_phase:.2f}: {scan_depth * 1e6:.0f} ppm ({scan_snr:.1f}σ){note}"
            )
        else:
            status = PASS
            message = f"no significant eclipse at phase 0.5 ({measured}){note}"
    elif limit is not None and depth > config.secondary_planet_factor * limit:
        status = FAIL
        message = (
            f"significant eclipse at phase 0.5 ({measured}), deeper than any planetary "
            f"occultation (≤{limit * 1e6:.0f} ppm): self-luminous companion{note}"
        )
    elif limit is not None:
        status = PASS
        message = (
            f"eclipse at phase 0.5 ({measured}) is within the planetary maximum "
            f"({limit * 1e6:.0f} ppm): consistent with a hot planet's occultation{note}"
        )
    else:
        status = WARN
        message = (
            f"significant eclipse at phase 0.5 ({measured}); "
            f"no fit available to judge whether a planet could produce it{note}"
        )
    return TestResult("secondary", status, float(snr), message, details)


def fit_trapezoid(lc: LightCurve, period: float, t0: float, duration: float) -> dict[str, float]:
    """Least-squares trapezoid fit to the phase-folded transit."""
    offset = fold(lc.time, period, t0)
    near = np.abs(offset) < 2.0 * duration
    x, y = offset[near], lc.flux[near]
    if x.size < 10:
        return {}
    width = max(duration / 30.0, np.median(np.diff(np.sort(lc.time))))
    xb, yb, _, nb = bin_timeseries(x, y, width=width)
    baseline = np.median(y[np.abs(x) > duration]) if np.any(np.abs(x) > duration) else 1.0
    yb = yb / baseline
    depth0 = max(1.0 - np.min(yb), 1e-5)
    weights = np.sqrt(nb)

    def resid(p: np.ndarray) -> np.ndarray:
        return (trapezoid(xb, p[0], p[1], p[2], p[3]) - yb) * weights

    starts = [0.2, 0.5, 0.9]
    best = None
    for f0 in starts:
        res = least_squares(
            resid,
            x0=[0.0, depth0, duration, f0],
            bounds=(
                [-duration / 4, 0.0, 0.3 * duration, 0.01],
                [duration / 4, 1.0, 2.5 * duration, 1.0],
            ),
        )
        if best is None or res.cost < best.cost:
            best = res
    assert best is not None
    dof = max(xb.size - 4, 1)
    try:
        cov = np.linalg.inv(best.jac.T @ best.jac) * (2 * best.cost / dof)
        errs = np.sqrt(np.clip(np.diag(cov), 0, None))
    except np.linalg.LinAlgError:
        errs = np.full(4, np.nan)
    return {
        "tc": float(best.x[0]),
        "depth": float(best.x[1]),
        "t14": float(best.x[2]),
        "ingress_fraction": float(best.x[3]),
        "ingress_fraction_err": float(errs[3]),
    }


def shape_test(
    lc: LightCurve,
    period: float,
    t0: float,
    duration: float,
    b_samples: np.ndarray | None = None,
    k_samples: np.ndarray | None = None,
    config: VetConfig | None = None,
) -> TestResult:
    """V-shape vs U-shape: trapezoid ingress fraction and posterior grazing probability."""
    config = config or VetConfig()
    trap = fit_trapezoid(lc, period, t0, duration)
    if not trap:
        return TestResult("shape", NA, float("nan"), "too few points in transit", {})
    metric = trap["ingress_fraction"]
    details: dict[str, Any] = {"trapezoid": trap}
    p_grazing = None
    if b_samples is not None and k_samples is not None:
        p_grazing = float(np.mean(np.asarray(b_samples) + np.asarray(k_samples) > 1.0))
        details["p_grazing"] = p_grazing
    v_like = metric >= config.v_shape_warn
    grazing = p_grazing is not None and p_grazing > 0.5
    status = WARN if (v_like or grazing) else PASS
    shape = "V-shaped" if v_like else ("U-shaped" if metric < 0.5 else "intermediate")
    message = f"{shape}: ingress+egress = {metric:.2f} of the duration"
    if p_grazing is not None:
        message += f"; posterior P(grazing) = {p_grazing:.2f}"
    return TestResult("shape", status, float(metric), message, details)


def density_tension(log_fit: np.ndarray, log_cat: float, sd_cat: float) -> float:
    """Signed, Gaussian-equivalent tension between posterior samples and a catalogue value.

    ``log_fit`` holds posterior samples of ln(density); ``log_cat`` and ``sd_cat``
    are the catalogue's ln(density) and its uncertainty. The probability that the
    transit-implied density lies at or beyond the catalogue value, on the side away
    from the posterior's median, is the mean over samples of
    ``Phi(±(x - log_cat) / sd_cat)``. It is turned into standard deviations with the
    inverse normal distribution, in log space so that extreme tensions stay finite.
    The sign is that of the posterior median's offset from the catalogue value.
    """
    x = np.asarray(log_fit, dtype=float)
    offset = float(np.median(x)) - log_cat
    d = (x - log_cat) / sd_cat
    # below the catalogue: the tail is the mass at or above it, and vice versa
    log_tail = logsumexp(log_ndtr(d if offset < 0 else -d)) - math.log(x.size)
    return math.copysign(max(-float(ndtri_exp(log_tail)), 0.0), offset)


def density_test(
    rho_fit_samples: np.ndarray | None,
    stellar: StellarParams | None,
    config: VetConfig | None = None,
) -> TestResult:
    """Compare the transit-implied stellar density with the catalogue density.

    The significance of a mismatch is the posterior probability that the
    transit-implied density lies at or beyond the catalogue value, with the
    catalogue's uncertainty (log-normal) folded in, expressed in Gaussian standard
    deviations. For a log-normal posterior this is the difference of the log
    densities over their combined width. Unlike that ratio, it stays right when
    the posterior is lopsided or has two modes, as when a fit wanders between a
    grazing and a non-grazing solution: the long tail on the far side then no
    longer dilutes a mismatch that no posterior sample comes near.
    """
    config = config or VetConfig()
    rho_cat, rho_cat_err = (None, None) if stellar is None else stellar.density_solar()
    if rho_fit_samples is None or rho_cat is None:
        return TestResult("density", NA, float("nan"), "no fitted or catalogue density", {})
    samples = np.asarray(rho_fit_samples, dtype=float)
    samples = samples[np.isfinite(samples) & (samples > 0)]
    if samples.size == 0:
        return TestResult("density", NA, float("nan"), "no fitted or catalogue density", {})
    log_fit = np.log(samples)
    mu_fit = float(np.median(log_fit))
    sd_cat = (rho_cat_err / rho_cat) if rho_cat_err else 0.0
    if not sd_cat:
        sd_cat = 0.25  # an uncertainty-free catalogue value is still only good to ~25 %
    z = density_tension(log_fit, math.log(rho_cat), sd_cat)
    ratio = math.exp(mu_fit) / rho_cat
    details = {
        "rho_fit_median": math.exp(mu_fit),
        "rho_fit_lo": float(np.percentile(samples, 15.865)),
        "rho_fit_hi": float(np.percentile(samples, 84.135)),
        "rho_catalog": rho_cat,
        "rho_catalog_err": rho_cat_err,
        "ratio": ratio,
        "catalog_source": stellar.source if stellar else None,
    }
    if abs(z) <= config.density_sigma:
        status = PASS
    elif max(ratio, 1 / ratio) > config.density_factor_fail:
        status = FAIL
    else:
        status = WARN
    message = (
        f"transit-implied ρ* = {math.exp(mu_fit):.2f} ρ☉ vs catalogue {rho_cat:.2f} ρ☉ "
        f"(ratio {ratio:.2f}, {abs(z):.1f}σ)"
    )
    return TestResult("density", status, float(z), message, details)


def radius_test(
    rp_rs_samples: np.ndarray | None, stellar: StellarParams | None, config: VetConfig | None = None
) -> TestResult:
    """Supplementary: is the companion too large to be a planet?"""
    config = config or VetConfig()
    if rp_rs_samples is None or stellar is None or not stellar.radius:
        return TestResult("radius", NA, float("nan"), "no stellar radius", {})
    rp = float(np.median(rp_rs_samples)) * stellar.radius * R_SUN / R_JUP
    status = FAIL if rp > config.max_planet_radius_rjup else PASS
    return TestResult("radius", status, rp, f"companion radius {rp:.2f} R_Jup", {"rp_rjup": rp})


def rotation_period(
    lc: LightCurve, mask: np.ndarray | None = None, min_period: float = 0.1
) -> dict[str, float]:
    """Rotation period from the Lomb-Scargle periodogram of an un-detrended light curve.

    ``lc`` is the cleaned, normalised light curve *before* detrending; ``mask``
    marks points to leave out (the transits of detected signals, whose own
    periodicity would otherwise show up). The light curve is binned to 30
    minutes and searched between ``min_period`` and half the baseline. Returns the
    period of the highest peak, its normalised power (the share of the binned
    light curve's variance that a sinusoid at that period explains), and the
    sinusoid's semi-amplitude in ppm. SPOC's PDC step can suppress variability on
    timescales longer than ~10 days, so long rotation periods are unreliable.
    """
    nan = float("nan")
    data = lc if mask is None else lc.select(~np.asarray(mask, dtype=bool))
    if len(data) < 10 or data.baseline <= 2 * min_period:
        return {"period": nan, "power": nan, "amplitude_ppm": nan}
    binned = data.bin(30.0 / 1440.0)
    f_lo, f_hi = 2.0 / data.baseline, 1.0 / min_period
    freq = np.arange(f_lo, f_hi, 0.2 / data.baseline)  # 5x oversampled
    ls = LombScargle(binned.time, binned.flux)
    power = ls.power(freq)
    best = int(np.argmax(power))
    coeffs = ls.model_parameters(freq[best])  # offset, sin, cos
    return {
        "period": float(1.0 / freq[best]),
        "power": float(power[best]),
        "amplitude_ppm": float(math.hypot(coeffs[1], coeffs[2]) * 1e6),
    }


def rotation_test(
    period: float, rotation: dict[str, float] | None, config: VetConfig | None = None
) -> TestResult:
    """Warn if the candidate's period is half, once, or twice the rotation period."""
    config = config or VetConfig()
    prot = (rotation or {}).get("period", float("nan"))
    power = (rotation or {}).get("power", float("nan"))
    details = dict(rotation or {})
    if not (np.isfinite(prot) and np.isfinite(power) and power >= config.rotation_min_power):
        return TestResult("rotation", NA, float("nan"), "no clear rotational modulation", details)
    offsets = {k: period / (k * prot) - 1.0 for k in (1.0, 0.5, 2.0)}
    k, offset = min(offsets.items(), key=lambda item: abs(item[1]))
    details.update(multiple=k, offset=offset)
    where = {1.0: "the rotation period", 0.5: "half the rotation period", 2.0: "twice it"}[k]
    if abs(offset) <= config.rotation_tolerance:
        message = (
            f"period is within {100 * abs(offset):.1f} % of {where} ({prot:.2f} d, "
            f"{details.get('amplitude_ppm', float('nan')):.0f} ppm): residual starspot "
            "modulation can mimic a transit there"
        )
        return TestResult("rotation", WARN, offset, message, details)
    message = f"period is not near the rotation period ({prot:.2f} d) or its multiples"
    return TestResult("rotation", PASS, offset, message, details)


def transit_coverage(
    lc: LightCurve, period: float, t0: float, duration: float
) -> list[dict[str, float]]:
    """Data coverage of every transit epoch with data in or next to the transit.

    For each epoch: the share of the expected cadences present inside the transit
    (``inside``) and in flanks one duration wide before and after it.
    """
    t = lc.time
    expected = duration / lc.cadence
    epochs = np.round((t - t0) / period)
    offset = t - (t0 + epochs * period)
    near = np.abs(offset) < 1.5 * duration
    out = []
    for epoch in np.unique(epochs[near]):
        x = offset[near & (epochs == epoch)]
        out.append(
            {
                "epoch": int(epoch),
                "tc": float(t0 + epoch * period),
                "inside": float(min(np.sum(np.abs(x) < duration / 2) / expected, 1.0)),
                "before": float(min(np.sum(x < -duration / 2) / expected, 1.0)),
                "after": float(min(np.sum(x > duration / 2) / expected, 1.0)),
            }
        )
    return out


def _fully_covered(epoch: dict[str, float], config: VetConfig) -> bool:
    return bool(
        epoch["inside"] >= config.coverage_min and epoch["before"] >= 0.5 and epoch["after"] >= 0.5
    )


def coverage_test(
    lc: LightCurve, period: float, t0: float, duration: float, config: VetConfig | None = None
) -> TestResult:
    """Fail a signal none of whose transits is covered by data inside and on both sides."""
    config = config or VetConfig()
    epochs = [e for e in transit_coverage(lc, period, t0, duration) if e["inside"] > 0]
    full = [e for e in epochs if _fully_covered(e, config)]
    partial = [round(e["tc"], 4) for e in epochs if not _fully_covered(e, config)]
    details = {"n_with_data": len(epochs), "n_fully_covered": len(full), "partial_tc": partial}
    if not epochs:
        return TestResult("coverage", NA, float("nan"), "no transit with data", details)
    message = (
        f"{len(full)} of {len(epochs)} transits with data are fully covered "
        "(inside and on both sides)"
    )
    if not full:
        message += (
            ": every event lies at the edge of a data segment, where instrumental "
            "systematics are common"
        )
        return TestResult("coverage", FAIL, 0.0, message, details)
    if len(full) < 2:
        return TestResult(
            "coverage", WARN, 1.0, message + ": the signal rests on one complete transit", details
        )
    return TestResult("coverage", PASS, float(len(full)), message, details)


def momentum_dump_test(
    lc: LightCurve, period: float, t0: float, duration: float, config: VetConfig | None = None
) -> TestResult | None:
    """Fail a signal whose dip comes from transits at momentum dumps.

    The dump times are ``lc.meta["momentum_dumps"]`` (see
    :func:`transit_hunter.data.momentum_dumps`); without them, as for a simulated
    light curve, there is nothing to test and None is returned. A transit is at a
    dump when the dump falls inside it or within ``dump_margin_hours`` of it.
    The transits measured by :func:`transit_depths` are split into those at dumps
    and the rest, and the weighted mean depths compared: when the transits at
    dumps are deeper by ``dump_sigma`` and the rest show no dip at that
    significance, the dip comes from the dumps and the signal fails; deeper alone
    gives a warning (a real transit can be distorted by a dump). When every
    transit is at a dump, the chance of that is the share of the data that lies
    near a dump, to the power of the number of transits: below ``dump_chance`` it
    fails.
    """
    config = config or VetConfig()
    if "momentum_dumps" not in lc.meta:
        return None
    dumps = np.sort(np.asarray(lc.meta["momentum_dumps"], dtype=float))
    window = duration / 2 + config.dump_margin_hours / 24

    def near_dump(times: np.ndarray) -> np.ndarray:
        if dumps.size == 0:
            return np.zeros(np.shape(times), dtype=bool)
        i = np.searchsorted(dumps, times)
        before = dumps[np.clip(i - 1, 0, dumps.size - 1)]
        after = dumps[np.clip(i, 0, dumps.size - 1)]
        return np.minimum(np.abs(times - before), np.abs(times - after)) <= window

    depths = transit_depths(lc, period, t0, duration)
    details: dict[str, Any] = {"n_dumps": int(dumps.size), "n_transits": len(depths)}
    if not depths:
        return TestResult("momentum_dumps", NA, float("nan"), "no transit measured", details)
    at = near_dump(np.array([x["tc"] for x in depths]))
    details["at_dump_tc"] = [round(x["tc"], 4) for x, a in zip(depths, at, strict=True) if a]
    k, n = int(at.sum()), len(depths)
    hours = f"{config.dump_margin_hours:g} h"
    if k == 0:
        return TestResult(
            "momentum_dumps", PASS, 0.0, f"no transit within {hours} of a momentum dump", details
        )

    def mean(group: list[dict[str, float]]) -> tuple[float, float]:
        w = np.array([1 / x["depth_err"] ** 2 for x in group])
        d = np.array([x["depth"] for x in group])
        return float(np.sum(w * d) / np.sum(w)), float(1 / math.sqrt(np.sum(w)))

    d_at, e_at = mean([x for x, a in zip(depths, at, strict=True) if a])
    if k == n:
        chance = float(np.mean(near_dump(lc.time))) ** n
        details.update(depth_at_dumps=d_at, chance=chance)
        message = (
            f"all {n} transits fall within {hours} of a momentum dump"
            if n > 1
            else f"the only transit falls within {hours} of a momentum dump"
        )
        if n >= 2 and chance < config.dump_chance:
            return TestResult(
                "momentum_dumps", FAIL, chance, message + f" (chance {chance:.1g})", details
            )
        return TestResult(
            "momentum_dumps", WARN, chance, message + f" (chance {chance:.2g})", details
        )
    d_away, e_away = mean([x for x, a in zip(depths, at, strict=True) if not a])
    sigma = (d_at - d_away) / math.hypot(e_at, e_away)
    details.update(depth_at_dumps=d_at, depth_elsewhere=d_away, sigma=sigma)
    message = (
        f"{k} of {n} transits fall within {hours} of a momentum dump: depth there "
        f"{d_at * 1e6:.0f}±{e_at * 1e6:.0f} ppm, "
        f"elsewhere {d_away * 1e6:.0f}±{e_away * 1e6:.0f} ppm"
    )
    if sigma > config.dump_sigma and d_away < config.dump_sigma * e_away:
        message += ": the dip comes from the dumps"
        return TestResult("momentum_dumps", FAIL, sigma, message, details)
    if sigma > config.dump_sigma:
        message += f": deeper at the dumps ({sigma:.1f}σ)"
        return TestResult("momentum_dumps", WARN, sigma, message, details)
    return TestResult("momentum_dumps", PASS, sigma, message, details)


#: Builds, for the time stamps of one transit window, a function of the shift dt (days)
#: returning the template's relative flux with its mid-transit time moved by dt.
TemplateFactory = Callable[[np.ndarray], Callable[[float], np.ndarray]]


def transit_depths(
    lc: LightCurve, period: float, t0: float, duration: float
) -> list[dict[str, float]]:
    """Depth of every transit with data inside it and on at least one side.

    The depth is the median flux of the flanks (0.75 to 2 durations from
    mid-transit) minus the median of the central 70 % of the transit, so it
    needs no transit model. A transit cut by a gap is measured against the flank
    it has (``sides`` is then 1): partial transits are the ones most often
    distorted by the systematics at the edges of the data, so they must be
    judged too. The uncertainty is that of the two medians, from the
    red-noise-inflated per-point scatter. ``step`` is the change of the
    out-of-transit level across the transit (before minus after; NaN with one
    flank): a transit on an instrumental ramp stands out in both.
    """
    sigma, beta = noise_properties(lc, period, t0, duration)
    out = []
    for epoch in transit_coverage(lc, period, t0, duration):
        dt = lc.time - epoch["tc"]
        inside = np.abs(dt) < 0.35 * duration
        pre = (dt > -2.0 * duration) & (dt < -0.75 * duration)
        post = (dt > 0.75 * duration) & (dt < 2.0 * duration)
        n_in, n_pre, n_post = int(inside.sum()), int(pre.sum()), int(post.sum())
        if n_in < 5 or max(n_pre, n_post) < 5:
            continue
        flanks = (pre if n_pre >= 5 else False) | (post if n_post >= 5 else False)
        n_flank = int(np.sum(flanks))
        level = float(np.median(lc.flux[flanks]))
        both = n_pre >= 5 and n_post >= 5
        out.append(
            {
                "epoch": epoch["epoch"],
                "tc": epoch["tc"],
                "depth": level - float(np.median(lc.flux[inside])),
                # a median's standard error is ~1.25 sigma / sqrt(n)
                "depth_err": 1.2533 * sigma * beta * math.sqrt(1 / n_in + 1 / n_flank),
                "step": float(np.median(lc.flux[pre]) - np.median(lc.flux[post]))
                if both
                else float("nan"),
                "sides": 2 if both else 1,
            }
        )
    return out


def bad_transits(
    lc: LightCurve, period: float, t0: float, duration: float, config: VetConfig | None = None
) -> tuple[list[dict[str, float]], dict[str, float]]:
    """Transits whose depth is far from the others': usually an instrumental event.

    With at least ``bad_transit_min_count`` measured transits (see
    :func:`transit_depths`), a transit stands out when its depth differs from
    the median by more than ``bad_transit_sigma`` times the larger of the
    robust scatter of the depths and their median uncertainty. Outliers must be
    rare: if more than ``bad_transit_max_fraction`` of the transits (and more
    than one) stand out, the depths are not one population with a stray
    member, and none is flagged. An eclipsing binary found at half its period is
    the case in point: the robust scatter follows the larger of its two groups
    of eclipses, the whole other group stands out, and dropping part of it would
    weaken the odd/even test that exposes the binary. Returns the flagged
    transits, most discrepant first, and the statistics used.
    """
    config = config or VetConfig()
    depths = transit_depths(lc, period, t0, duration)
    stats: dict[str, float] = {"n_measured": len(depths)}
    if len(depths) < config.bad_transit_min_count:
        return [], stats
    d = np.array([x["depth"] for x in depths])
    median = float(np.median(d))
    scatter = 1.4826 * float(np.median(np.abs(d - median)))
    scale = max(scatter, float(np.median([x["depth_err"] for x in depths])))
    stats.update(median_depth=median, scatter=scatter, scale=scale)
    if scale <= 0:
        return [], stats
    deviation = np.abs(d - median) / scale
    outliers = np.flatnonzero(deviation > config.bad_transit_sigma)
    stats["n_standing_out"] = int(outliers.size)
    if outliers.size > max(1, int(config.bad_transit_max_fraction * len(depths))):
        return [], stats
    flagged = [
        depths[i] | {"deviation": float(deviation[i])}
        for i in outliers[np.argsort(deviation[outliers])[::-1]]
    ]
    return flagged, stats


def chunk_consistency(
    lc: LightCurve, period: float, t0: float, duration: float, max_gap: float = 0.5
) -> dict[str, Any]:
    """Whether the transits are equally deep in separate chunks of the data.

    A planet's transits are equally deep in every sector; a dip made by one
    sector's systematics, or by a star that only one sector's aperture takes in,
    is not. The chunks are the sectors when the transits fall in several, and
    otherwise the stretches of data between gaps longer than ``max_gap`` days (a
    sector's two spacecraft orbits). Each transit's depth comes from
    :func:`transit_depths`. As in the odd/even test, a chunk's uncertainty is
    raised to at least the scatter of single-transit depths about their own
    chunk's median, divided by the square root of their number, so that ordinary
    transit-to-transit variation does not count as a difference; taking the
    scatter within each chunk keeps a dip confined to one chunk from inflating it.

    Returns each chunk's depth and S/N, the S/N of all chunks together and
    without the one with the highest S/N, and a chi-square test of equal depths
    (``p_value`` is None with fewer than two chunks). This is a diagnostic, not a
    vetting test: the batch search uses it to rank candidates.
    """
    out: dict[str, Any] = {
        "n_transits": 0,
        "n_chunks": 0,
        "chunked_by": "sector",
        "chunks": [],
        "snr_all": float("nan"),
        "snr_without_strongest": float("nan"),
        "strongest": None,
        "chi2": float("nan"),
        "dof": 0,
        "p_value": None,
        "scatter_floor": 0.0,
    }
    depths = transit_depths(lc, period, t0, duration)
    if not depths:
        return out
    tc = np.array([x["tc"] for x in depths])
    d = np.array([x["depth"] for x in depths])
    e = np.array([x["depth_err"] for x in depths])
    nearest = np.clip(np.searchsorted(lc.time, tc), 0, lc.time.size - 1)
    if lc.sector is not None and np.unique(lc.sector[nearest]).size > 1:
        labels = [f"sector {int(s)}" for s in lc.sector[nearest]]
    else:
        out["chunked_by"] = "segment"
        bounds = segment_bounds(lc.time, max_gap)
        starts = np.array([lc.time[a] for a, _ in bounds])
        labels = [f"segment {int(np.searchsorted(starts, t, side='right'))}" for t in tc]
    names = list(dict.fromkeys(labels))
    groups = [np.array([lab == name for lab in labels]) for name in names]
    # Scatter of single-transit depths about their own chunk's median, pooled over
    # the chunks with enough transits to measure it.
    deviations = np.concatenate(
        [d[g] - np.median(d[g]) for g in groups if g.sum() >= 3] or [np.array([])]
    )
    scatter = 1.4826 * float(np.median(np.abs(deviations))) if deviations.size >= 6 else 0.0
    chunks = []
    for name, g in zip(names, groups, strict=True):
        w = 1.0 / e[g] ** 2
        depth = float(np.sum(w * d[g]) / np.sum(w))
        err = max(float(1.0 / math.sqrt(np.sum(w))), scatter / math.sqrt(int(g.sum())))
        chunks.append(
            {
                "chunk": name,
                "n_transits": int(g.sum()),
                "depth": depth,
                "depth_err": err,
                "snr": depth / err if err > 0 else float("nan"),
            }
        )

    def combined(items: list[dict[str, Any]]) -> tuple[float, float]:
        w = np.array([1.0 / c["depth_err"] ** 2 for c in items])
        mean = float(np.sum(w * [c["depth"] for c in items]) / np.sum(w))
        return mean, float(1.0 / math.sqrt(np.sum(w)))

    mean, err = combined(chunks)
    out.update(
        n_transits=len(depths),
        n_chunks=len(chunks),
        chunks=chunks,
        snr_all=mean / err,
        scatter_floor=scatter,
    )
    if len(chunks) >= 2:
        strongest = max(chunks, key=lambda c: c["snr"])
        rest_mean, rest_err = combined([c for c in chunks if c is not strongest])
        chi2 = float(sum((c["depth"] - mean) ** 2 / c["depth_err"] ** 2 for c in chunks))
        out.update(
            strongest=strongest["chunk"],
            snr_without_strongest=rest_mean / rest_err,
            chi2=chi2,
            dof=len(chunks) - 1,
            p_value=float(chi2_dist.sf(chi2, len(chunks) - 1)),
        )
    return out


def without_transits(lc: LightCurve, times: list[float], duration: float) -> LightCurve:
    """``lc`` without the data within two durations of each mid-transit time in ``times``.

    That is the transit and the flanks :func:`transit_depths` measures it against.
    """
    keep = np.ones(len(lc), dtype=bool)
    for tc in times:
        keep &= np.abs(lc.time - tc) >= 2.0 * duration
    return lc.select(keep)


def dropped_transits_note(flagged: list[dict[str, float]], stats: dict[str, float]) -> str:
    """One line for a vetting report listing the transits left out by :func:`bad_transits`."""

    def level(x: dict[str, float]) -> str:
        step = x.get("step")
        if step is None or not math.isfinite(step):
            return "data on one side only"
        return f"out-of-transit level {step * 1e6:+.0f} ppm higher before than after"

    items = "; ".join(
        f"BTJD {x['tc']:.3f}: {x['depth'] * 1e6:.0f}±{x['depth_err'] * 1e6:.0f} ppm deep, "
        f"{level(x)}"
        for x in flagged
    )
    n_rest = int(stats["n_measured"]) - len(flagged)
    return (
        f"[note] left out before the fit and the tests, as far from the depth of the other "
        f"{n_rest} measured transits (median {stats['median_depth'] * 1e6:.0f} ppm, "
        f"scatter {stats['scale'] * 1e6:.0f} ppm): {items}"
    )


def template_from_params(
    params: TransitParams, supersample: int = 1, exp_time: float = 0.0
) -> TemplateFactory:
    """A :data:`TemplateFactory` for a fixed batman transit shape."""

    def factory(time: np.ndarray) -> Callable[[float], np.ndarray]:
        model = BatmanModel(time, supersample, exp_time)
        return lambda dt: model.from_params(replace(params, t0=params.t0 + dt))

    return factory


def measure_transit_times(
    lc: LightCurve,
    period: float,
    t0: float,
    duration: float,
    template: TemplateFactory,
    epochs: list[dict[str, float]],
) -> list[dict[str, float]]:
    """Mid-transit time of each given epoch, with the transit shape held fixed.

    The shift of the template and a multiplicative baseline are fitted to the
    data within 1.5 durations of the predicted time; the uncertainty comes from
    the curvature of chi-square, inflated by the reduced chi-square when that
    exceeds one. Correlated noise is not included, so the uncertainties are
    lower limits. Used to diagnose transit-timing variations (TTVs): folded on a
    single period, transits whose times vary are smeared, which biases the
    fitted shape and the transit-implied stellar density.
    """
    out = []
    for epoch in epochs:
        tc = epoch["tc"]
        sel = np.abs(lc.time - tc) < 1.5 * duration
        f, w = lc.flux[sel], 1.0 / lc.flux_err[sel] ** 2
        shifted = template(lc.time[sel])

        def chi2(dt: float, f: np.ndarray = f, w: np.ndarray = w, shifted: Any = shifted) -> float:
            m = shifted(dt)
            scale = np.sum(w * f * m) / np.sum(w * m * m)
            return float(np.sum(w * (f - scale * m) ** 2))

        res = minimize_scalar(
            chi2,
            bounds=(-0.5 * duration, 0.5 * duration),
            method="bounded",
            options={"xatol": 1e-6},
        )
        h = duration / 200.0
        curvature = (chi2(res.x + h) - 2.0 * res.fun + chi2(res.x - h)) / h**2
        n = int(sel.sum())
        if curvature <= 0 or n < 10:
            continue
        sigma = math.sqrt(2.0 / curvature) * math.sqrt(max(1.0, res.fun / (n - 2)))
        out.append({"epoch": epoch["epoch"], "tc": tc + float(res.x), "err": sigma})
    return out


# --------------------------------------------------------------------------- orchestration
def run_vetting(
    lc: LightCurve,
    period: float,
    t0: float,
    duration: float,
    fit: Any | None = None,
    stellar: StellarParams | None = None,
    config: VetConfig | None = None,
    depth: float | None = None,
    rotation: dict[str, float] | None = None,
    pixels: PixelSource | None = None,
) -> VettingReport:
    """Run every test.

    ``fit`` is a :class:`transit_hunter.fit.FitResult` (optional). Without a fit,
    the radius ratio and a/R* needed for the planetary-occultation limit are
    estimated from the BLS ``depth`` and duration (k ~ sqrt(depth),
    a/R* ~ (1 + k) P / (pi T14), i.e. a central transit).

    ``lc`` should still contain any other eclipse of the same system (a
    same-period signal at another phase): masking it would hide the secondary
    eclipse from the test designed to find it. ``rotation`` is the output of
    :func:`rotation_period` for the un-detrended light curve (optional).
    ``pixels`` gives the target-pixel files for the centroid test; without it
    (a simulated light curve, say) that test is not run at all, while a source
    whose pixels turn out to be unavailable makes it "n/a".
    """
    config = config or VetConfig()
    model = rp_rs = a_rs = None
    b_s = k_s = rho_s = None
    if depth is not None and depth > 0 and duration > 0:
        rp_rs = math.sqrt(depth)
        a_rs = max((1.0 + rp_rs) * period / (math.pi * duration), 1.0)
    if fit is not None:
        best = fit.best_params()
        period, t0 = best["period"], best["t0"]
        duration = float(np.median(fit.derived["t14_hours"])) / 24.0
        model = fit.fitter.model_flux(fit.best, lc.time) / best["f0"]
        params = fit.param_samples()
        b_s, k_s = params["b"], params["rp_rs"]
        rho_s = fit.derived["rho_star_solar"]
        rp_rs = float(np.median(k_s))
        a_rs = float(np.median(fit.derived["a_rs"]))
    teff = stellar.teff if stellar is not None else None
    tests = [
        odd_even_test(lc, period, t0, duration, model, config),
        secondary_eclipse_test(lc, period, t0, duration, rp_rs, a_rs, teff, config),
        shape_test(lc, period, t0, duration, b_s, k_s, config),
        density_test(rho_s, stellar, config),
        radius_test(k_s, stellar, config),
        coverage_test(lc, period, t0, duration, config),
        momentum_dump_test(lc, period, t0, duration, config),
        rotation_test(period, rotation, config),
    ]
    tests = [t for t in tests if t is not None]  # the dump test needs the dump times
    centroid = None
    if pixels is not None:
        try:
            centroid = measure_centroid(
                pixels,
                lc,
                period,
                t0,
                duration,
                depth,
                config.centroid_floor_arcsec,
                config.centroid_min_snr,
                config.centroid_max_sectors,
            )
            tests.append(centroid_test(centroid, config.centroid_sigma))
        except Exception as exc:  # unusual pixel data must not stop a batch run
            log.warning("centroid test failed: %s", exc, exc_info=True)
            centroid = None
            tests.append(TestResult("centroid", NA, float("nan"), f"could not run ({exc})"))
    verdict, reasons = decide(tests)
    return VettingReport(tests, verdict, reasons, centroid)


#: Tests whose "n/a" is an answer rather than a gap: no rotational modulation
#: means there is no rotation period for a signal to coincide with.
NA_IS_A_RESULT = frozenset({"rotation"})


def decide(tests: list[TestResult]) -> tuple[str, list[str]]:
    """Combine test outcomes into a verdict with human-readable reasons.

    Any failed test marks the signal a likely false positive. Warnings, or tests
    that could not run (for example the density and radius tests without a
    catalogue stellar radius), leave it a planet candidate "with caveats": a
    signal is only said to pass all tests if every test ran. These diagnostics
    cannot rule out a blended eclipsing binary closer to the target than the
    centroid test resolves (that needs high-resolution imaging), so a clean
    result means "consistent with a planet", not "confirmed".
    """
    failed = [t for t in tests if t.status == FAIL]
    warned = [t for t in tests if t.status == WARN]
    untested = [t for t in tests if t.status == NA and t.name not in NA_IS_A_RESULT]
    reasons = [f"[{t.status}] {t.name}: {t.message}" for t in tests]
    if failed:
        verdict = "likely false positive"
    elif warned or untested:
        verdict = "planet candidate (with caveats)"
        if untested:
            names = ", ".join(t.name for t in untested)
            reasons.append(f"not tested: {names}, so the verdict rests on the other tests")
    else:
        verdict = "planet candidate (passes all tests)"
    return verdict, reasons


# --------------------------------------------------------------------------- plot
_STATUS_COLOR = {PASS: STATUS_GOOD, WARN: STATUS_WARNING, FAIL: STATUS_CRITICAL, NA: INK_MUTED}


def plot_vetting(
    lc: LightCurve,
    period: float,
    t0: float,
    duration: float,
    report: VettingReport,
    path: str | Path,
    title: str = "",
    fit: Any | None = None,
) -> Path:
    """Four diagnostic panels: odd/even, phase 0.5, transit shape, density."""
    if fit is not None:
        best = fit.best_params()
        period, t0 = best["period"], best["t0"]
        duration = float(np.median(fit.derived["t14_hours"])) / 24.0
    hours = fold(lc.time, period, t0) * 24
    win = 2.0 * duration * 24
    bin_h = max(duration * 24 / 12, 2 / 60)
    epochs = epoch_index(lc.time, period, t0)
    with style():
        fig, axes = new_figure(2, 2, figsize=(11, 7.4))
        (ax_oe, ax_sec), (ax_shape, ax_rho) = axes

        oe = report.test("odd_even")
        for parity, sel, color in (
            ("odd", epochs % 2 == 1, BLUE),
            ("even", epochs % 2 == 0, ORANGE),
        ):
            use = sel & (np.abs(hours) < win)
            hb, fb, eb, _ = bin_timeseries(hours[use], lc.flux[use], width=bin_h)
            ax_oe.errorbar(
                hb, (fb - 1) * 1e6, yerr=eb * 1e6, fmt="o", ms=3.5, lw=1, color=color, label=parity
            )
            depth = oe.details.get(parity, {}).get("depth")
            if depth is not None and np.isfinite(depth):
                ax_oe.axhline(-depth * 1e6, color=color, lw=1.0)
        ax_oe.set_xlim(-win, win)
        ax_oe.set_xlabel("hours from mid-transit")
        ax_oe.set_ylabel("flux − 1 (ppm)")
        ax_oe.legend(loc="lower right")
        _panel_title(ax_oe, "odd / even depths", oe)

        sec = report.test("secondary")
        sec_hours = fold(lc.time, period, t0 + 0.5 * period) * 24
        use = np.abs(sec_hours) < 3 * duration * 24
        ax_sec.plot(
            sec_hours[use],
            (lc.flux[use] - 1) * 1e6,
            ".",
            ms=1,
            color=INK_MUTED,
            alpha=0.35,
            rasterized=True,
        )
        hb, fb, eb, _ = bin_timeseries(sec_hours[use], lc.flux[use], width=2 * bin_h)
        ax_sec.errorbar(hb, (fb - 1) * 1e6, yerr=eb * 1e6, fmt="o", ms=3.5, lw=1, color=BLUE)
        ax_sec.axvspan(-duration * 12, duration * 12, color=AXIS, alpha=0.25, lw=0)
        spread = 6 * np.nanstd(fb - 1) * 1e6 if fb.size > 3 else 1000
        ax_sec.set_ylim(-spread, spread)
        ax_sec.set_xlabel("hours from phase 0.5")
        _panel_title(ax_sec, "secondary eclipse", sec)

        shp = report.test("shape")
        use = np.abs(hours) < win
        hb, fb, eb, _ = bin_timeseries(hours[use], lc.flux[use], width=bin_h)
        ax_shape.errorbar(
            hb,
            (fb - 1) * 1e6,
            yerr=eb * 1e6,
            fmt="o",
            ms=3.5,
            lw=1,
            color=BLUE,
            label="binned data",
        )
        trap = shp.details.get("trapezoid")
        if trap:
            grid = np.linspace(-win, win, 800)
            model = trapezoid(
                grid / 24, trap["tc"], trap["depth"], trap["t14"], trap["ingress_fraction"]
            )
            ax_shape.plot(grid, (model - 1) * 1e6, "-", color=ORANGE, lw=1.6, label="trapezoid")
        ax_shape.set_xlim(-win, win)
        ax_shape.set_xlabel("hours from mid-transit")
        ax_shape.set_ylabel("flux − 1 (ppm)")
        ax_shape.legend(loc="lower right")
        _panel_title(ax_shape, "transit shape", shp)

        rho = report.test("density")
        if fit is not None and "rho_star_solar" in fit.derived:
            samples = fit.derived["rho_star_solar"]
            lo, hi = np.percentile(samples, [0.5, 99.5])
            ax_rho.hist(
                samples,
                bins=np.linspace(lo, hi, 30),
                color=BLUE,
                alpha=0.85,
                label="transit-implied",
                histtype="stepfilled",
            )
            cat = rho.details.get("rho_catalog")
            if cat:
                err = rho.details.get("rho_catalog_err") or 0.0
                ax_rho.axvline(cat, color=INK, lw=1.4, label="catalogue")
                if err:
                    ax_rho.axvspan(cat - err, cat + err, color=AXIS, alpha=0.35, lw=0)
            ax_rho.set_xlabel("mean stellar density (ρ☉)")
            ax_rho.set_ylabel("posterior samples")
            ax_rho.legend(loc="upper right")
        else:
            ax_rho.text(
                0.5,
                0.5,
                "no MCMC fit",
                ha="center",
                va="center",
                color=INK_SECONDARY,
                transform=ax_rho.transAxes,
            )
            ax_rho.set_xticks([])
            ax_rho.set_yticks([])
            ax_rho.grid(False)
        _panel_title(ax_rho, "stellar density", rho)

        fig.suptitle(
            f"{title}  —  verdict: {report.verdict}" if title else report.verdict,
            x=0.01,
            ha="left",
            fontsize=12,
            fontweight="bold",
        )
        return save_figure(fig, path)


def _panel_title(ax: Any, name: str, test: TestResult) -> None:
    """Panel title in ink with a coloured status dot (colour never carries meaning alone)."""
    ax.set_title(f"    {name}: {test.status.upper()}", loc="left", fontsize=10, color=INK)
    ax.text(
        0.0,
        1.0,
        "●",
        transform=ax.transAxes,
        fontsize=13,
        va="bottom",
        ha="left",
        color=_STATUS_COLOR.get(test.status, INK_MUTED),
    )
    ax.text(
        0.0,
        -0.22,
        test.message,
        transform=ax.transAxes,
        fontsize=7.5,
        color=INK_SECONDARY,
        va="top",
        wrap=True,
    )
