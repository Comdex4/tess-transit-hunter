"""False-positive vetting diagnostics.

Eclipsing binaries (EBs) -- on the target or blended with it -- are the main
astrophysical impostors of transiting planets. Each test below looks for a
specific EB signature; none needs pixel data.

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

import math
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np
from astropy.timeseries import LombScargle
from scipy.optimize import least_squares, minimize_scalar

from .catalog import StellarParams
from .lightcurve import LightCurve
from .models import BatmanModel, TransitParams
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
from .utils import R_JUP, R_SUN, bin_timeseries, binned_rms, epoch_index, fold, robust_std

PASS, WARN, FAIL, NA = "pass", "warn", "fail", "n/a"


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
    rotation_min_power: float = 0.1  # Lomb-Scargle power needed to trust a rotation period


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
    inflates the estimate.
    """
    phase = fold(lc.time, period, t0)
    phase_sec = fold(lc.time, period, t0 + 0.5 * period)
    oot = (np.abs(phase) > duration) & (np.abs(phase_sec) > duration)
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
    """Compare transit depths of odd and even epochs."""
    config = config or VetConfig()
    sigma, beta = noise_properties(lc, period, t0, duration)
    near = np.abs(fold(lc.time, period, t0)) < 1.5 * duration
    template = _shape_template(lc, period, t0, duration, model)
    baseline = np.median(lc.flux[~near]) if np.any(~near) else 1.0
    y = baseline - lc.flux
    epochs = epoch_index(lc.time, period, t0)
    results = {}
    for parity, sel in (("odd", epochs % 2 == 1), ("even", epochs % 2 == 0)):
        use = near & sel
        n_transits = int(np.unique(epochs[use & (template > 0.5)]).size)
        amp, err = _amplitude(y[use], template[use], sigma * beta)
        results[parity] = {"depth": amp, "depth_err": err, "n_transits": n_transits}
    odd, even = results["odd"], results["even"]
    if min(odd["n_transits"], even["n_transits"]) < 1 or not np.isfinite(odd["depth_err"]):
        return TestResult(
            "odd_even",
            NA,
            float("nan"),
            "need at least one odd and one even transit",
            results | {"beta": beta},
        )
    diff = odd["depth"] - even["depth"]
    err = math.hypot(odd["depth_err"], even["depth_err"])
    significance = abs(diff) / err
    status = FAIL if significance > config.odd_even_sigma else PASS
    message = (
        f"odd depth {odd['depth'] * 1e6:.0f}±{odd['depth_err'] * 1e6:.0f} ppm vs even "
        f"{even['depth'] * 1e6:.0f}±{even['depth_err'] * 1e6:.0f} ppm: "
        f"{significance:.1f}σ difference"
    )
    return TestResult(
        "odd_even",
        status,
        significance,
        message,
        results | {"difference": diff, "difference_err": err, "beta": beta},
    )


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
    """Search for an occultation at phase 0.5 (and report the strongest dip at any phase)."""
    config = config or VetConfig()
    sigma, beta = noise_properties(lc, period, t0, duration)
    offset = fold(lc.time, period, t0 + 0.5 * period)
    depth, err, n_in = _box_depth(offset, lc.flux, duration, sigma, beta)
    details: dict[str, Any] = {"depth": depth, "depth_err": err, "n_points": n_in, "beta": beta}

    # Phase scan (eccentric orbits): exclude +/- 1.5 durations around the primary.
    phase_primary = fold(lc.time, period, t0)
    step = max(duration / 4.0, period / 2000.0)
    best = (float("-inf"), float("nan"), float("nan"))
    keep = np.abs(phase_primary) > 1.5 * duration
    for centre in np.arange(2.0 * duration, period - 2.0 * duration, step):
        off = fold(lc.time[keep], period, t0 + centre)
        d, e, _ = _box_depth(off, lc.flux[keep], duration, sigma, beta)
        if np.isfinite(d) and d / e > best[0]:
            best = (d / e, centre / period, d)
    details.update({"scan_max_snr": best[0], "scan_phase": best[1], "scan_depth": best[2]})

    if not np.isfinite(depth):
        return TestResult("secondary", NA, float("nan"), "no data near phase 0.5", details)
    snr = depth / err
    limit = None
    if rp_rs is not None and a_rs is not None:
        limit = max_planet_occultation(rp_rs, a_rs, teff)
        details["max_planet_depth"] = limit
    measured = f"{depth * 1e6:.0f}±{err * 1e6:.0f} ppm, {snr:.1f}σ"
    scan_snr, scan_phase, scan_depth = best
    scan_significant = bool(np.isfinite(scan_snr) and scan_snr >= config.secondary_scan_sigma)
    if snr < config.secondary_sigma:
        if (
            scan_significant
            and limit is not None
            and scan_depth > config.secondary_planet_factor * limit
        ):
            status = FAIL
            message = (
                f"no eclipse at phase 0.5 ({measured}), but a {scan_depth * 1e6:.0f} ppm dip "
                f"({scan_snr:.1f}σ) at phase {scan_phase:.2f}, deeper than any planetary "
                f"occultation (≤{limit * 1e6:.0f} ppm): eccentric eclipsing binary?"
            )
        elif scan_significant:
            status = WARN
            message = (
                f"no eclipse at phase 0.5 ({measured}); strongest dip at phase "
                f"{scan_phase:.2f}: {scan_depth * 1e6:.0f} ppm ({scan_snr:.1f}σ)"
            )
        else:
            status = PASS
            message = f"no significant eclipse at phase 0.5 ({measured})"
    elif limit is not None and depth > config.secondary_planet_factor * limit:
        status = FAIL
        message = (
            f"significant eclipse at phase 0.5 ({measured}), deeper than any planetary "
            f"occultation (≤{limit * 1e6:.0f} ppm): self-luminous companion"
        )
    elif limit is not None:
        status = PASS
        message = (
            f"eclipse at phase 0.5 ({measured}) is within the planetary maximum "
            f"({limit * 1e6:.0f} ppm): consistent with a hot planet's occultation"
        )
    else:
        status = WARN
        message = (
            f"significant eclipse at phase 0.5 ({measured}); "
            "no fit available to judge whether a planet could produce it"
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


def density_test(
    rho_fit_samples: np.ndarray | None,
    stellar: StellarParams | None,
    config: VetConfig | None = None,
) -> TestResult:
    """Compare the transit-implied stellar density with the catalogue density."""
    config = config or VetConfig()
    rho_cat, rho_cat_err = (None, None) if stellar is None else stellar.density_solar()
    if rho_fit_samples is None or rho_cat is None:
        return TestResult("density", NA, float("nan"), "no fitted or catalogue density", {})
    samples = np.asarray(rho_fit_samples, dtype=float)
    samples = samples[np.isfinite(samples) & (samples > 0)]
    log_fit = np.log(samples)
    mu_fit = float(np.median(log_fit))
    sd_fit = float(0.5 * (np.percentile(log_fit, 84.135) - np.percentile(log_fit, 15.865)))
    sd_cat = (rho_cat_err / rho_cat) if rho_cat_err else 0.0
    if not sd_cat:
        sd_cat = 0.25  # an uncertainty-free catalogue value is still only good to ~25 %
    z = (mu_fit - math.log(rho_cat)) / math.hypot(sd_fit, sd_cat)
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


#: Builds, for the time stamps of one transit window, a function of the shift dt (days)
#: returning the template's relative flux with its mid-transit time moved by dt.
TemplateFactory = Callable[[np.ndarray], Callable[[float], np.ndarray]]


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
        rotation_test(period, rotation, config),
    ]
    verdict, reasons = decide(tests)
    return VettingReport(tests, verdict, reasons)


def decide(tests: list[TestResult]) -> tuple[str, list[str]]:
    """Combine test outcomes into a verdict with human-readable reasons.

    Any failed test marks the signal a likely false positive. Warnings alone
    leave it a planet candidate "with caveats". These diagnostics cannot rule
    out blends with a background eclipsing binary (that needs pixel-level
    centroid analysis and high-resolution imaging), so a clean result means
    "consistent with a planet", not "confirmed".
    """
    failed = [t for t in tests if t.status == FAIL]
    warned = [t for t in tests if t.status == WARN]
    reasons = [f"[{t.status}] {t.name}: {t.message}" for t in tests]
    if failed:
        verdict = "likely false positive"
    elif warned:
        verdict = "planet candidate (with caveats)"
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
