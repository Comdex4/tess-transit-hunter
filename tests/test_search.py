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
    find_signal,
    harmonic_relation,
    iterative_search,
    make_period_grid,
    plot_folded,
    plot_periodogram,
    plot_search_summary,
    red_noise_snr,
    sde_spectrum,
    sinusoid_test,
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


def test_same_period_second_eclipse_is_flagged():
    """An EB with unequal eclipses: the second eclipse is not reported as a new planet."""
    from transit_hunter.models import TransitParams, transit_model

    noise = NoiseModel(white_ppm=400, red_ppm=0, rotation_ppm=500, rotation_period=8.0)
    lc = simulate_lightcurve(noise=noise, n_sectors=2, seed=55)
    # Secondary much shallower than the primary, so the full period has clearly the
    # higher likelihood. (With similar eclipses BLS prefers half the period, which the
    # odd/even vetting test then catches; see test_pipeline_flags_eclipsing_binaries.)
    primary = TransitParams(2001.0, 5.6, 0.12, 11.0, 0.1, 0.45, 0.2)
    secondary = TransitParams(2001.0 + 2.8, 5.6, 0.055, 11.0, 0.1, 0.45, 0.2)
    lc = lc.with_flux(lc.flux * transit_model(lc.time, primary) * transit_model(lc.time, secondary))
    result = iterative_search(
        detrend(lc).flat, SearchConfig(max_signals=3, stellar_density=1.0), raw=lc
    )
    assert len(result.detections) == 2
    first, second = result.detections
    assert second.secondary_of == 0 and first.secondary_of is None
    assert second.phase_offset == pytest.approx(0.5, abs=0.01)
    assert result.candidates == [first]


def test_same_period_relation_ignores_coincident_transits():
    from transit_hunter.search import same_period_relation

    first = _signal(5.0, 100.0)
    assert same_period_relation(_signal(5.001, 102.5), [first]) == (0, pytest.approx(0.5))
    assert same_period_relation(_signal(5.0, 100.02), [first]) is None  # same transits
    assert same_period_relation(_signal(6.0, 102.5), [first]) is None
    # Found at P/2 after the primary transits were masked: its transits with data all
    # sit at phase 0.5 of the earlier period.
    half = _signal(2.5, 102.5)
    half.transit_times = [102.5, 107.5, 112.5]
    assert same_period_relation(half, [first]) == (0, pytest.approx(0.5))
    # ... but a P/2 alias whose transits alternate between both phases is not.
    alias = _signal(2.5, 102.5)
    alias.transit_times = [100.0, 102.5, 105.0, 107.5]
    assert same_period_relation(alias, [first]) is None


def test_strong_planet_is_reported_at_its_true_period_not_an_alias():
    """Regression: a deep transit's broad periodogram hump must not hand the peak to P/2."""
    star = SyntheticStar()
    noise = NoiseModel(white_ppm=700, red_ppm=60, rotation_ppm=1500, rotation_period=10.0)
    planet = planet_from_physical(1.575, 5.9, star, t0=2000.9, b=0.34)
    lc = simulate_lightcurve(star, noise, [planet], n_sectors=2, seed=2024)
    result = iterative_search(
        detrend(lc).flat, SearchConfig(max_signals=2, stellar_density=1.0), raw=lc
    )
    assert result.detections[0].period == pytest.approx(1.575, rel=2e-3)


def test_coherent_stellar_modulation_is_not_a_detection(rng):
    """Regression: a residual starspot sinusoid is rejected, not reported as a transit."""
    t = np.arange(2000.0, 2055.0, 10 / 1440)
    flux = 1 + 2e-4 * np.sin(2 * np.pi * t / 4.3) + rng.normal(0, 3e-4, t.size)
    lc = LightCurve(t, flux, np.full(t.size, 3e-4))
    signal, _ = find_signal(lc, SearchConfig(stellar_density=1.0))
    assert signal is None or not (signal.detected and abs(signal.period / 4.3 - 1) < 0.01)
    skipped = [s for s in (signal.skipped_peaks if signal else []) if "sinusoid" in s["reason"]]
    assert any(abs(s["period"] / 4.3 - 1) < 0.01 for s in skipped)


def test_sinusoid_test_separates_transits_from_modulation(rng):
    t = np.arange(2000.0, 2027.0, 10 / 1440)
    noise = rng.normal(0, 2e-4, t.size)
    err = np.full(t.size, 2e-4)
    period, t0, duration = 3.0, 2001.0, 0.3
    q = duration / period
    # Share of a box's variance carried by its fundamental.
    f = 2 * math.sin(math.pi * q) ** 2 / (math.pi**2 * q * (1 - q))
    box = 1 - 1e-3 * (np.abs(fold(t, period, t0)) < duration / 2) + noise
    result = sinusoid_test(LightCurve(t, box, err), period, t0, duration)
    assert result.box_fraction == pytest.approx(f, rel=0.02)
    assert result.ratio == pytest.approx(1.0, abs=0.1)
    assert result.chi2 < 13.8
    # A box fitted to the trough of a sinusoid implies a sinusoid 1/f times weaker.
    sine = 1 - 1e-3 * np.cos(2 * np.pi * (t - t0) / period) + noise
    result = sinusoid_test(LightCurve(t, sine, err), period, t0, duration)
    assert result.ratio == pytest.approx(1 / f, rel=0.05)
    assert result.chi2 > 1000


def test_sinusoid_test_flags_modulation_with_harmonics(rng):
    """Spot-like modulation (fundamental + harmonic): the box sits off the fundamental's trough."""
    t = np.arange(2000.0, 2055.0, 10 / 1440)
    period = 4.0

    def spots(x):
        return 3e-4 * np.sin(2 * np.pi * x / period) + 2e-4 * np.sin(4 * np.pi * x / period + 1.0)

    grid = np.linspace(2000.0, 2000.0 + period, 2000, endpoint=False)
    trough = grid[np.argmin(spots(grid))]
    lc = LightCurve(t, 1 + spots(t) + rng.normal(0, 5e-4, t.size), np.full(t.size, 5e-4))
    result = sinusoid_test(lc, period, trough, 0.3)
    assert result.ratio > 1.75 and result.chi2 > 13.8


def test_sinusoid_test_is_calibrated_for_box_shaped_dips(rng):
    """For a box in white noise chi2 follows chi-square(2), even for long duty cycles."""
    t = np.arange(2000.0, 2027.0, 10 / 1440)
    period, t0, duration = 0.6, 2000.2, 0.12  # duty cycle 0.2, as at the shortest periods
    in_transit = np.abs(fold(t, period, t0)) < duration / 2
    depth = 7 * 1e-3 / math.sqrt(in_transit.sum())  # white-noise S/N ~ 7
    err = np.full(t.size, 1e-3)
    chi2 = np.array(
        [
            sinusoid_test(
                LightCurve(t, 1 - depth * in_transit + rng.normal(0, 1e-3, t.size), err),
                period,
                t0,
                duration,
            ).chi2
            for _ in range(400)
        ]
    )
    assert chi2.mean() == pytest.approx(2.0, abs=0.3)
    assert np.mean(chi2 > 13.8) < 0.01


def test_short_period_planet_is_not_mistaken_for_variability(sun_like_star):
    """Regression: a transit with a long duty cycle (P = 0.535 d) must not be skipped.

    A sinusoid captures 53 % of its box's likelihood gain, above the fixed 50 % limit
    first used to reject stellar variability, and its chi2 (17.9) also exceeds the
    white-noise limit, so only the amplitude-ratio condition keeps it.
    """
    noise = NoiseModel(
        white_ppm=700, red_ppm=60, red_timescale=0.04, rotation_ppm=1500, rotation_period=10.0
    )
    planet = planet_from_physical(0.535, 1.2, sun_like_star, t0=2000.3, b=0.2)
    lc = simulate_lightcurve(sun_like_star, noise, [planet], n_sectors=2, seed=43)
    signal, _ = find_signal(detrend(lc).flat, SearchConfig(stellar_density=1.0))
    assert signal.detected and signal.period == pytest.approx(0.535, rel=2e-3)
    assert signal.sinusoid_ratio < 1.75


def test_resolve_harmonic_prefers_the_highest_power_family_member():
    from transit_hunter.search import Periodogram, _resolve_harmonic

    period = np.geomspace(0.5, 10, 20000)
    power = np.ones(period.size)
    for p, value in ((1.0, 50.0), (2.0, 100.0), (4.0, 50.0)):
        power[np.argmin(np.abs(period - p))] = value
    zeros = np.zeros(period.size)
    pg = Periodogram(period, power, zeros, zeros, zeros + 0.1, zeros, zeros)
    at_half = int(np.argmin(np.abs(period - 1.0)))
    assert period[_resolve_harmonic(pg, at_half)] == pytest.approx(2.0, rel=1e-3)
    at_true = int(np.argmin(np.abs(period - 2.0)))
    assert _resolve_harmonic(pg, at_true) == at_true
