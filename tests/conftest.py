"""Shared fixtures. Every test uses synthetic data only -- no network access."""

from __future__ import annotations

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")

from transit_hunter.synthetic import (
    NoiseModel,
    SyntheticStar,
    planet_from_physical,
    simulate_lightcurve,
)


@pytest.fixture(scope="session")
def sun_like_star() -> SyntheticStar:
    return SyntheticStar(radius=1.0, mass=1.0, teff=5770.0)


@pytest.fixture(scope="session")
def quiet_noise() -> NoiseModel:
    """Low-noise, low-variability star (bright, quiet G dwarf)."""
    return NoiseModel(white_ppm=200.0, red_ppm=0.0, rotation_ppm=500.0, rotation_period=8.0)


@pytest.fixture(scope="session")
def single_planet_lc(sun_like_star, quiet_noise):
    """Two sectors, 2-min cadence, one 3-Earth-radius planet on a 3.3-day orbit."""
    planet = planet_from_physical(3.3, 3.0, sun_like_star, t0=2001.7, b=0.3)
    lc = simulate_lightcurve(sun_like_star, quiet_noise, [planet], n_sectors=2, seed=11)
    return lc, planet


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(1234)
