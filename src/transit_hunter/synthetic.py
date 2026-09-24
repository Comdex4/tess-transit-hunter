"""Synthetic TESS-like light curves.

Used by the test-suite, by the offline demo, and to calibrate detection
thresholds and completeness when real data are not at hand. Nothing in this
module is ever presented as a measurement of a real star.

The simulated photometry reproduces the features of SPOC 2-minute data that
matter for transit searches:

* sampling: 2-min cadence, 27.4-day sectors split into two spacecraft orbits by
  a ~1-day data-downlink gap;
* stellar variability: quasi-periodic starspot modulation whose amplitude and
  phase evolve on a few rotation periods;
* correlated ("red") noise: an Ornstein-Uhlenbeck (damped random walk) process
  standing in for granulation and residual pointing jitter;
* white noise, plus (optionally) positive outliers, flagged cadences, and NaNs.

Transits are multiplied into the stellar flux with ``batman``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .data import QUALITY_FLAGS, SectorData
from .lightcurve import LightCurve
from .models import TransitParams, a_rs_from_mass_radius, transit_model
from .utils import R_EARTH, R_SUN, RHO_SUN


@dataclass
class SyntheticStar:
    """Host-star properties (solar units, K)."""

    radius: float = 1.0
    mass: float = 1.0
    teff: float = 5770.0

    @property
    def density(self) -> float:
        """Mean density in kg m^-3."""
        return self.mass / self.radius**3 * RHO_SUN


@dataclass
class NoiseModel:
    """Amplitudes are in parts per million of the stellar flux."""

    white_ppm: float = 300.0
    red_ppm: float = 50.0
    red_timescale: float = 0.05
    rotation_ppm: float = 1000.0
    rotation_period: float = 6.0
    outlier_rate: float = 0.0
    outlier_ppm: float = 3000.0


@dataclass
class SyntheticPlanet:
    """A transiting planet (circular orbit)."""

    period: float
    t0: float
    rp_rs: float
    a_rs: float
    b: float = 0.3
    u1: float = 0.4
    u2: float = 0.2

    def to_params(self) -> TransitParams:
        return TransitParams(self.t0, self.period, self.rp_rs, self.a_rs, self.b, self.u1, self.u2)


def planet_from_physical(
    period: float,
    radius_earth: float,
    star: SyntheticStar,
    t0: float,
    b: float = 0.3,
    u1: float = 0.4,
    u2: float = 0.2,
) -> SyntheticPlanet:
    """Build a planet from its period (days) and radius (Earth radii)."""
    rp_rs = radius_earth * R_EARTH / (star.radius * R_SUN)
    a_rs = a_rs_from_mass_radius(period, star.mass, star.radius)
    return SyntheticPlanet(period, t0, rp_rs, a_rs, b, u1, u2)


def tess_timestamps(
    n_sectors: int = 1,
    cadence_minutes: float = 2.0,
    start: float = 2000.0,
    sector_length: float = 27.4,
    downlink_gap: float = 1.0,
    sector_gap: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Time stamps (BTJD) and sector numbers for ``n_sectors`` TESS-like sectors.

    Each sector consists of two equal spacecraft orbits separated by a
    ``downlink_gap``; consecutive sectors are separated by ``sector_gap`` days.
    """
    cadence = cadence_minutes / 1440.0
    orbit = 0.5 * (sector_length - downlink_gap)
    times, sectors = [], []
    for s in range(n_sectors):
        t_start = start + s * (sector_length + sector_gap)
        for o in range(2):
            t0 = t_start + o * (orbit + downlink_gap)
            t = np.arange(t0, t0 + orbit, cadence)
            times.append(t)
            sectors.append(np.full(t.size, s + 1))
    return np.concatenate(times), np.concatenate(sectors)


def ou_noise(time: np.ndarray, sigma: float, tau: float, rng: np.random.Generator) -> np.ndarray:
    """Ornstein-Uhlenbeck process with stationary rms ``sigma`` and timescale ``tau``.

    Uses the exact discretisation ``x_{i+1} = x_i e^{-dt/tau} + sigma sqrt(1 - e^{-2dt/tau}) N``,
    which stays correct across irregular sampling and data gaps.
    """
    x = np.empty(time.size)
    if time.size == 0 or sigma <= 0:
        return np.zeros(time.size)
    x[0] = sigma * rng.standard_normal()
    decay = np.exp(-np.diff(time) / tau)
    kicks = sigma * np.sqrt(1.0 - decay**2) * rng.standard_normal(time.size - 1)
    for i in range(1, time.size):
        x[i] = x[i - 1] * decay[i - 1] + kicks[i - 1]
    return x


def rotational_modulation(
    time: np.ndarray,
    amplitude: float,
    period: float,
    rng: np.random.Generator,
    n_harmonics: int = 2,
    evolution_periods: float = 2.0,
) -> np.ndarray:
    """Quasi-periodic starspot signal with evolving amplitude and phase.

    Each harmonic's amplitude and phase follow smooth random walks with a
    correlation time of ``evolution_periods`` rotations, mimicking spot
    emergence and decay.
    """
    if amplitude <= 0 or time.size == 0:
        return np.zeros(time.size)
    grid = np.arange(time.min(), time.max() + period / 5.0, period / 10.0)
    tau = evolution_periods * period
    signal = np.zeros(time.size)
    for h in range(1, n_harmonics + 1):
        weight = 1.0 / h
        amp = amplitude * weight * (1.0 + 0.3 * ou_noise(grid, 1.0, tau, rng))
        phase = rng.uniform(0, 2 * np.pi) + 0.5 * ou_noise(grid, 1.0, tau, rng)
        amp_t = np.interp(time, grid, np.clip(amp, 0.0, None))
        phase_t = np.interp(time, grid, phase)
        signal += amp_t * np.sin(2 * np.pi * h * time / period + phase_t)
    return signal


def simulate_lightcurve(
    star: SyntheticStar | None = None,
    noise: NoiseModel | None = None,
    planets: Sequence[SyntheticPlanet] = (),
    n_sectors: int = 1,
    cadence_minutes: float = 2.0,
    seed: int | None = None,
    start: float = 2000.0,
    sector_gap: float = 0.0,
) -> LightCurve:
    """Simulate a normalised, cleaned (PDCSAP-like) light curve.

    The returned light curve contains stellar variability, noise, and the
    requested transits, but no flagged cadences. The ground truth is recorded
    in ``meta["truth"]``.
    """
    star = star or SyntheticStar()
    noise = noise or NoiseModel()
    rng = np.random.default_rng(seed)
    time, sector = tess_timestamps(n_sectors, cadence_minutes, start, sector_gap=sector_gap)

    stellar = 1.0 + 1e-6 * (
        rotational_modulation(time, noise.rotation_ppm, noise.rotation_period, rng)
        + ou_noise(time, noise.red_ppm, noise.red_timescale, rng)
    )
    transit = np.ones(time.size)
    cadence = cadence_minutes / 1440.0
    supersample = max(1, math.ceil(cadence_minutes / 2.0))
    for planet in planets:
        transit *= transit_model(
            time,
            planet.to_params(),
            supersample_factor=supersample,
            exp_time=cadence if supersample > 1 else 0.0,
        )
    white = 1e-6 * noise.white_ppm
    flux = stellar * transit + white * rng.standard_normal(time.size)
    if noise.outlier_rate > 0:
        hit = rng.random(time.size) < noise.outlier_rate
        flux[hit] += 1e-6 * noise.outlier_ppm * rng.exponential(1.0, hit.sum())
    flux_err = np.full(time.size, white)

    truth = {
        "star": star.__dict__.copy(),
        "noise": noise.__dict__.copy(),
        "planets": [p.__dict__.copy() for p in planets],
        "seed": seed,
        "cadence_minutes": cadence_minutes,
    }
    return LightCurve(time, flux, flux_err, sector, {"synthetic": True, "truth": truth})


@dataclass
class RawSimulationOptions:
    """Artefacts added to raw (pre-cleaning) simulated SPOC sectors."""

    flux_level: float = 5.0e4  # e-/s
    momentum_dump_interval: float = 3.1  # days between reaction-wheel desaturations
    flagged_fraction: float = 0.01  # random cadences with a 'bad' quality bit and junk flux
    nan_fraction: float = 0.005
    outlier_rate: float = 0.002
    outlier_ppm: float = 5000.0


def simulate_raw_sectors(
    lc: LightCurve,
    options: RawSimulationOptions | None = None,
    seed: int | None = None,
) -> list[SectorData]:
    """Turn a clean simulated light curve into raw, SPOC-like per-sector data.

    Adds a QUALITY column (momentum dumps, randomly flagged cadences with
    corrupted flux), NaNs, and positive outliers, and scales the flux to
    electrons per second. Used to test :mod:`transit_hunter.data` offline.
    """
    options = options or RawSimulationOptions()
    rng = np.random.default_rng(seed)
    sectors = lc.sector if lc.sector is not None else np.ones(len(lc), dtype=int)
    out = []
    for s in np.unique(sectors):
        sel = sectors == s
        time = lc.time[sel].copy()
        flux = lc.flux[sel].copy()
        err = lc.flux_err[sel].copy()
        quality = np.zeros(time.size, dtype=np.int64)

        dumps = np.arange(time.min() + 1.0, time.max(), options.momentum_dump_interval)
        for t_dump in dumps:
            near = np.abs(time - t_dump) < 5.0 / 1440.0
            quality[near] |= QUALITY_FLAGS["Desat"]
            flux[near] *= 1.0 + rng.normal(0.0, 0.01, near.sum())  # junk photometry
        bad = rng.random(time.size) < options.flagged_fraction
        quality[bad] |= QUALITY_FLAGS["CoarsePoint"]
        flux[bad] *= 1.0 + rng.normal(0.0, 0.02, bad.sum())
        # Bits that the default bitmask must *not* remove:
        benign = rng.random(time.size) < 0.01
        quality[benign] |= QUALITY_FLAGS["ApertureCosmic"]

        nan = rng.random(time.size) < options.nan_fraction
        flux[nan] = np.nan
        outlier = (rng.random(time.size) < options.outlier_rate) & ~bad & ~nan
        flux[outlier] += 1e-6 * options.outlier_ppm * (1.0 + rng.exponential(1.0, outlier.sum()))

        header = {
            "SECTOR": int(s),
            "TICID": 0,
            "TEFF": 5770.0,
            "RADIUS": 1.0,
            "LOGG": 4.44,
            "TESSMAG": 9.0,
        }
        out.append(
            SectorData(
                int(s), time, flux * options.flux_level, err * options.flux_level, quality, header
            )
        )
    return out
