import math

import numpy as np
import pytest

from transit_hunter.detrend import detrend
from transit_hunter.lightcurve import LightCurve
from transit_hunter.search import (
    SearchConfig,
    Signal,
    bls_periodogram,
    central_duration,
    count_transits_with_data,
    duration_grid,
    effective_trials,
    harmonic_relation,
    iterative_search,
    make_period_grid,
    plot_folded,
    plot_periodogram,
    plot_search_summary,
    red_noise_snr,
    sde_spectrum,
    trial_corrected_threshold,
)
from transit_hunter.synthetic import (
    NoiseModel,
    SyntheticStar,
    planet_from_physical,
    simulate_lightcurve,
)
from transit_hunter.utils import fold


def test_central_duration_of_earth_around_sun():
    # Earth's central transit across the Sun lasts ~13 hours.
    assert central_duration(365.25, 1.0) * 24 == pytest.approx(13.0, rel=0.03)
    # Denser stars give shorter transits (T ∝ rho^-1/3).
    ratio = central_duration(10.0, 8.0) / central_duration(10.0, 1.0)
    assert ratio == pytest.approx(0.5, rel=0.02)


def test_duration_grid_is_geometric():
    cfg = SearchConfig(min_duration=0.02, max_duration=0.5, duration_ratio=1.25)
    grid = duration_grid(cfg)
    assert grid[0] == pytest.approx(0.02)
    assert grid[-1] <= 0.5
    np.testing.assert_allclose(grid[1:] / grid[:-1], 1.25)


def test_period_grid_spans_range_and_resolves_phase_drift():
    cfg = SearchConfig(frequency_oversample=3.0)
    baseline = 27.0
    grid = make_period_grid(baseline, cfg)
    periods = grid.periods
    assert periods.min() == pytest.approx(cfg.min_period)
    assert periods.max() == pytest.approx(baseline / 2)
    assert np.all(np.diff(periods) > 0)
    for band in grid.bands:
        # Durations must be shorter than every period in the band (astropy requirement).
        assert band.durations.max() < band.periods.min()
        # Log-frequency step no coarser than D_min / (OS * baseline).
        steps = np.diff(np.log(band.periods))
        assert steps.max() <= band.durations.min() / (3.0 * baseline) * 1.001
    # Long-period bands need longer minimum durations than short-period bands.
    assert grid.bands[-1].durations.min() >= grid.bands[0].durations.min()


def test_trial_correction_grows_with_baseline():
    short = effective_trials(make_period_grid(27.4, SearchConfig(stellar_density=1.0)))
    long = effective_trials(make_period_grid(700.0, SearchConfig(stellar_density=1.0)))
    assert long > 30 * short
    assert trial_corrected_threshold(1e6, 0.01) == pytest.approx(6.07, abs=0.01)
    assert trial_corrected_threshold(1e6, 0.01) < trial_corrected_threshold(1e8, 0.01)


def test_known_density_narrows_duration_grid():
    broad = make_period_grid(27.4, SearchConfig())
    narrow = make_period_grid(27.4, SearchConfig(stellar_density=1.0))
    assert sum(b.durations.size for b in narrow.bands) < sum(b.durations.size for b in broad.bands)
    # No trial duration exceeds the longest physical one for rho >= rho*/3 (with (1+k) <= 1.2).
    for band in narrow.bands:
        assert band.durations.max() <= 1.2 * central_duration(band.periods.max(), 1 / 3) + 1e-9


def test_period_grid_rejects_short_baseline():
    with pytest.raises(ValueError):
        make_period_grid(0.8, SearchConfig())


def test_sde_spectrum_is_standardised(rng):
    period = np.geomspace(0.5, 20, 5000)
    power = rng.chisquare(2, period.size) * (1 + 0.1 * np.log(period))  # rising noise floor
    sde = sde_spectrum(period, power)
    assert sde.mean() == pytest.approx(0.0, abs=1e-9)
    assert sde.std() == pytest.approx(1.0, rel=1e-6)
    # The rising trend is removed: short- and long-period halves have similar medians.
    half = period.size // 2
    assert abs(np.median(sde[:half]) - np.median(sde[half:])) < 0.3


@pytest.fixture(scope="module")
def single_search(single_planet_lc):
    """Iterative search of the one-planet light curve (Sun-like host, density known)."""
    lc, planet = single_planet_lc
    flat = detrend(lc).flat
    config = SearchConfig(max_signals=2, stellar_density=1.0)
    return flat, planet, iterative_search(flat, config, raw=lc)


def test_bls_recovers_injected_planet(single_search):
    _, planet, result = single_search
    sig = result.signals[0]
    assert sig.detected
    assert sig.period == pytest.approx(planet.period, rel=1e-3)
    # Mid-transit time matches the injected ephemeris to within 10 minutes.
    offset = fold(np.array([sig.t0]), planet.period, planet.t0)[0]
    assert abs(offset) * 1440 < 10
    true_t14 = planet.to_params().t14
    assert sig.duration == pytest.approx(true_t14, rel=0.5)
    # Box depth is a little below (Rp/Rs)^2 because of the transit shape.
    assert 0.6 * planet.rp_rs**2 < sig.depth < 1.2 * planet.rp_rs**2
    assert sig.snr > 10 and sig.sde > 7
    assert sig.n_transits >= 10
    # With one planet, the second iteration should find nothing significant.
    assert len(result.detections) == 1
    # The applied S/N threshold is at least the configured floor.
    assert sig.snr_threshold >= 7.0


def test_iterative_search_finds_two_planets_near_resonance():
    star = SyntheticStar(radius=0.5, mass=0.5)
    noise = NoiseModel(white_ppm=400, red_ppm=0, rotation_ppm=1000, rotation_period=9.0)
    inner = planet_from_physical(4.1, 2.5, star, t0=2000.6, b=0.2)
    # Period ratio 2.012: close to, but not in, 2:1 resonance.
    outer = planet_from_physical(8.25, 2.8, star, t0=2002.9, b=0.3)
    lc = simulate_lightcurve(star, noise, [inner, outer], n_sectors=2, seed=31)
    config = SearchConfig(max_signals=4, stellar_density=star.mass / star.radius**3)
    result = iterative_search(detrend(lc).flat, config, raw=lc)
    found = sorted(s.period for s in result.detections)
    assert len(found) == 2
    assert found[0] == pytest.approx(inner.period, rel=2e-3)
    assert found[1] == pytest.approx(outer.period, rel=2e-3)
    assert all(s.harmonic_of is None for s in result.detections)


def test_noise_only_light_curve_gives_no_detection():
    noise = NoiseModel(white_ppm=500, red_ppm=60, rotation_ppm=1500, rotation_period=5.0)
    lc = simulate_lightcurve(noise=noise, n_sectors=1, seed=77)
    result = iterative_search(detrend(lc).flat, SearchConfig())
    assert result.detections == []
    assert len(result.signals) <= 1


def _signal(period, t0, duration=0.1):
    return Signal(
        iteration=1,
        period=period,
        t0=t0,
        duration=duration,
        depth=1e-3,
        depth_err=1e-4,
        snr=10,
        snr_white=10,
        sde=10,
        power=1,
        n_transits=5,
    )


def test_harmonic_relation_requires_period_and_phase_match():
    first = _signal(5.0, 100.0)
    assert harmonic_relation(_signal(10.0, 105.0), [first]) == 0  # 2P, same transits
    assert harmonic_relation(_signal(2.5, 102.5), [first]) == 0  # P/2
    assert harmonic_relation(_signal(10.0, 102.3), [first]) is None  # 2P, other phase
    assert harmonic_relation(_signal(10.06, 105.0), [first]) is None  # near-resonant
    assert harmonic_relation(_signal(7.3, 100.0), [first]) is None


def test_count_transits_ignores_gaps():
    t = np.concatenate([np.arange(0, 10, 0.01), np.arange(20, 30, 0.01)])
    # Transits every 2.5 d starting at t = 1: those at 11, 13.5, 16, 18.5 fall in the gap.
    assert count_transits_with_data(t, 2.5, 1.0, 0.1) == 8


def test_red_noise_snr_grows_as_root_n(rng):
    t = np.arange(0, 54, 2 / 1440)
    flux = 1 + rng.normal(0, 1e-3, t.size)
    lc = LightCurve(t, flux, np.full(t.size, 1e-3))
    snr4 = red_noise_snr(lc, 5.0, 1.0, 0.1, 5e-4, 4)
    snr16 = red_noise_snr(lc, 5.0, 1.0, 0.1, 5e-4, 16)
    assert snr16 / snr4 == pytest.approx(2.0, rel=1e-6)
    # For white noise: depth / (sigma / sqrt(n_per_transit * n_transits)).
    expected = 5e-4 / (1e-3 / math.sqrt(0.1 / (2 / 1440)) / 2)
    assert snr4 == pytest.approx(expected, rel=0.1)


def test_parallel_periodogram_matches_serial(single_planet_lc):
    lc, _ = single_planet_lc
    flat = detrend(lc).flat.bin(30 / 1440)
    cfg = SearchConfig(max_period=6.0, frequency_oversample=1.0)
    serial = bls_periodogram(flat, cfg)
    parallel = bls_periodogram(
        flat, SearchConfig(max_period=6.0, frequency_oversample=1.0, n_workers=2)
    )
    np.testing.assert_allclose(serial.period, parallel.period)
    np.testing.assert_allclose(serial.power, parallel.power)


def test_search_plots_are_written(tmp_path, single_search):
    flat, _, result = single_search
    sig = result.signals[0]
    paths = [
        plot_periodogram(result.periodograms[0], sig, tmp_path / "pg.png", sde_threshold=7),
        plot_folded(flat, sig, tmp_path / "fold.png", title="test"),
        plot_search_summary(result, flat, tmp_path / "summary.png"),
    ]
    for path in paths:
        assert path.exists() and path.stat().st_size > 10_000
