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
    edge_events,
    effective_trials,
    eligible_trials,
    find_signal,
    folded_brightening,
    harmonic_relation,
    iterative_search,
    make_period_grid,
    mask_edge_events,
    plot_folded,
    plot_periodogram,
    plot_search_summary,
    red_noise_snr,
    sde_spectrum,
    single_events,
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


def test_eligible_trials_need_two_transits_with_data():
    # Two ten-day stretches of data, 90 days apart.
    t = np.concatenate([np.arange(0.0, 10.0, 2 / 1440), np.arange(100.0, 110.0, 2 / 1440)])
    period = np.array([3.0, 50.0, 50.0, 60.0])
    t0 = np.array([1.0, 5.0, 30.0, 2.0])
    ok = eligible_trials(t, period, t0, np.full(4, 0.2))
    # 3 d: two whole boxes fit in either stretch at any phase. 50 d from 5: transits at
    # 5 and 105 have data. 50 d from 30, and 60 d from 2, have one or none.
    assert ok.tolist() == [True, True, False, False]


def test_sde_is_standardised_on_the_reference_trials(rng):
    period = np.geomspace(0.5, 200, 20000)
    power = rng.chisquare(2, period.size)
    power[9000] = 60.0  # a real signal among the eligible trials
    single = (period > 50) & (rng.random(period.size) < 0.7)
    power[single] *= 20  # boxes on one strong dip, which can never be detections
    plain = sde_spectrum(period, power)
    sde = sde_spectrum(period, power, reference=~single)
    assert sde[~single].mean() == pytest.approx(0.0, abs=1e-9)
    assert sde[~single].std() == pytest.approx(1.0, rel=1e-6)
    assert sde[9000] > 2 * plain[9000]


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
    """Regression: a residual starspot wave is rejected, not reported as a transit."""
    t = np.arange(2000.0, 2055.0, 10 / 1440)
    flux = 1 + 2e-4 * np.sin(2 * np.pi * t / 4.3) + rng.normal(0, 3e-4, t.size)
    lc = LightCurve(t, flux, np.full(t.size, 3e-4))
    signal, _ = find_signal(lc, SearchConfig(stellar_density=1.0))
    assert signal is None or not (signal.detected and abs(signal.period / 4.3 - 1) < 0.01)
    skipped = [s for s in (signal.skipped_peaks if signal else []) if "variability" in s["reason"]]
    assert any(abs(s["period"] / 4.3 - 1) < 0.01 for s in skipped)


def test_folded_brightening_separates_transits_from_modulation(rng):
    t = np.arange(2000.0, 2027.0, 10 / 1440)
    noise = rng.normal(0, 2e-4, t.size)
    err = np.full(t.size, 2e-4)
    period, t0 = 3.0, 2001.0
    for duration in (0.06, 0.3, 0.6):  # duty cycles 0.02, 0.1 and 0.2
        box = 1 - 1e-3 * (np.abs(fold(t, period, t0)) < duration / 2) + noise
        dip, bright = folded_brightening(LightCurve(t, box, err), period, t0, duration)
        # Only noise brightens a transit's folded light curve: a few sigma at most.
        assert dip > 40 and bright < 4.5
        # The trough of a sinusoid comes with a crest of the same significance.
        wave = 1 - 1e-3 * np.cos(2 * np.pi * (t - t0) / period) + noise
        dip, bright = folded_brightening(LightCurve(t, wave, err), period, t0, duration)
        assert bright == pytest.approx(dip, rel=0.15)


def test_folded_brightening_rarely_rejects_marginal_transits(rng):
    """A box at S/N ~ 7 in white noise: detectable dips are almost never rejected."""
    t = np.arange(2000.0, 2054.8, 10 / 1440)
    period, t0, duration = 4.0, 2000.7, 0.12
    in_transit = np.abs(fold(t, period, t0)) < duration / 2
    depth = 7 * 1e-3 / math.sqrt(in_transit.sum())
    err = np.full(t.size, 1e-3)
    results = []
    for _ in range(300):
        flux = 1 - depth * in_transit + rng.normal(0, 1e-3, t.size)
        results.append(folded_brightening(LightCurve(t, flux, err), period, t0, duration))
    dip, bright = np.array(results).T
    ratio = bright / dip
    assert np.median(ratio) < 0.45
    detectable = dip >= 7  # dips that could pass the S/N threshold
    assert detectable.sum() > 100
    assert np.mean(ratio[detectable] > SearchConfig().max_brightening_ratio) < 0.01


def test_short_period_planet_is_not_mistaken_for_variability(sun_like_star):
    """Regression: a transit with a long duty cycle (P = 0.535 d) must not be skipped.

    The first stellar-variability filter (skip a peak when a sinusoid captures more than
    half of the box model's likelihood gain) skipped it: the share was 53 %, because at
    such short periods a box already puts a large share of its variance into its
    fundamental.
    """
    noise = NoiseModel(
        white_ppm=700, red_ppm=60, red_timescale=0.04, rotation_ppm=1500, rotation_period=10.0
    )
    planet = planet_from_physical(0.535, 1.2, sun_like_star, t0=2000.3, b=0.2)
    lc = simulate_lightcurve(sun_like_star, noise, [planet], n_sectors=2, seed=43)
    signal, _ = find_signal(detrend(lc).flat, SearchConfig(stellar_density=1.0))
    assert signal.detected and signal.period == pytest.approx(0.535, rel=2e-3)
    assert signal.brightening_ratio < SearchConfig().max_brightening_ratio


def test_planet_at_half_the_rotation_period_is_not_mistaken_for_variability(sun_like_star):
    """Regression: residual spot modulation at the orbital period must not hide a planet.

    Here the planet's period is half the star's 10-day rotation period. A second
    filter design, which compared the light curve's sinusoid at the candidate period
    with the one the box implies, skipped it (the sinusoid was 3.4 times stronger than
    the transit implies, because of the residual modulation). The folded light curve
    brightens by only about a third of the dip's significance.
    """
    noise = NoiseModel(
        white_ppm=700, red_ppm=60, red_timescale=0.04, rotation_ppm=1500, rotation_period=10.0
    )
    planet = planet_from_physical(5.0, 1.9, sun_like_star, t0=2001.3, b=0.3)
    lc = simulate_lightcurve(sun_like_star, noise, [planet], n_sectors=2, seed=60)
    signal, _ = find_signal(detrend(lc).flat, SearchConfig(stellar_density=1.0))
    assert signal.detected and signal.period == pytest.approx(5.0, rel=2e-3)
    assert signal.brightening_ratio < 0.5


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


def _segmented_lc(seed: int, noise_ppm: float = 500.0) -> LightCurve:
    """White noise at a 2-min cadence in four segments separated by 1-day gaps."""
    rng = np.random.default_rng(seed)
    t = np.concatenate(
        [
            np.arange(a, b, 2 / 1440)
            for a, b in ((0.0, 6.0), (7.0, 10.0), (11.0, 17.0), (18.0, 27.0))
        ]
    )
    return LightCurve(t, 1 + rng.normal(0, noise_ppm * 1e-6, t.size), np.full(t.size, 5e-4))


def _dip(lc: LightCurve, centre: float, depth: float, width: float = 2 / 24) -> LightCurve:
    return lc.with_flux(lc.flux - depth * (np.abs(lc.time - centre) < width / 2))


def test_single_events_and_edge_events():
    lc = _dip(_dip(_segmented_lc(seed=5), 3.0, 3000e-6), 7.03, 3000e-6)
    lc = _dip(lc, 13.0, 150e-6)  # far too shallow to count
    config = SearchConfig()
    events = single_events(lc, duration_grid(config), 7.0)
    assert sorted(round(e["time"], 1) for e in events) == [3.0, 7.0]
    middle = next(e for e in events if abs(e["time"] - 3.0) < 0.1)
    assert middle["depth"] == pytest.approx(3000e-6, rel=0.2)
    assert middle["snr"] > 30
    # Only the dip that begins at the start of a segment lacks data on one side.
    edge = edge_events(lc, config)
    assert [round(e["time"], 1) for e in edge] == [7.0]
    masked, found = mask_edge_events(lc, config)
    assert found == edge
    assert not np.any(np.abs(masked.time - 7.03) < 0.04)
    assert np.any(np.abs(masked.time - 3.0) < 0.01)
    assert edge_events(lc, SearchConfig(edge_event_sigma=0)) == []


def _cut(lc: LightCurve, start: float, stop: float) -> LightCurve:
    """``lc`` without the cadences between ``start`` and ``stop`` (a short gap)."""
    return lc.select((lc.time < start) | (lc.time > stop))


def test_a_transit_cut_by_a_short_gap_is_not_an_edge_event():
    # A deep 2-hour dip three days inside a segment, 40 % of it lost to a short gap
    # (flagged cadences, a momentum dump): uncovered, but not at an edge of the data.
    lc = _cut(_dip(_segmented_lc(seed=8), 3.0, 3000e-6), 2.99, 3.023)
    assert edge_events(lc, SearchConfig()) == []
    # Counting every uncovered dip, wherever it lies, would mask it.
    anywhere = edge_events(lc, SearchConfig(edge_reach=100.0))
    assert [round(e["time"], 1) for e in anywhere] == [3.0]


def test_a_two_transit_planet_is_found_when_one_transit_is_cut_by_a_short_gap():
    # A 12.5-day planet with two transits in the data, at 2.5 and 15.0 d, the second
    # partly lost to a short gap two days from the nearest segment edge.
    lc = _segmented_lc(seed=9)
    for centre in (2.5, 15.0):
        lc = _dip(lc, centre, 2000e-6, width=3 / 24)
    lc = _cut(lc, 14.99, 15.03)
    signal, pg = find_signal(lc, SearchConfig())
    assert signal is not None and signal.detected
    assert signal.period == pytest.approx(12.5, rel=1e-3)
    assert pg.edge_events == []
    # Masking every uncovered dip removes one of its two transits.
    signal, _ = find_signal(lc, SearchConfig(edge_reach=100.0))
    assert signal is None or not (signal.detected and abs(signal.period / 12.5 - 1) < 1e-3)


def test_dips_at_segment_edges_no_longer_hide_a_shallow_planet():
    # HD 21749 c in miniature: a 300 ppm planet at S/N ~17, and four deep
    # instrumental dips just inside the ends of data segments. Every trial period
    # can put its box on such a dip, so they drown the planet unless masked.
    lc = _segmented_lc(seed=6)
    for n in range(12):
        lc = _dip(lc, 0.7 + 2.3 * n, 300e-6, width=2.5 / 24)
    for centre in (7.03, 11.03, 16.97, 26.97):
        lc = _dip(lc, centre, 5000e-6)
    hidden, _ = find_signal(lc, SearchConfig(edge_event_sigma=0))
    assert hidden is None or not (hidden.detected and abs(hidden.period / 2.3 - 1) < 1e-3)
    signal, pg = find_signal(lc, SearchConfig())
    assert signal is not None and signal.detected
    assert signal.period == pytest.approx(2.3, rel=1e-3)
    assert sorted(round(e["time"], 1) for e in pg.edge_events) == [7.0, 11.0, 17.0, 27.0]


def test_a_planet_with_a_transit_at_a_segment_edge_is_still_found():
    lc = _segmented_lc(seed=7)
    period, t0 = 3.1, 1.2
    for n in range(9):
        lc = _dip(lc, t0 + n * period, 1500e-6)
    # The transit at 16.7 d ends 0.2 d before a segment does and is fully covered;
    # the one at 10.5 d falls in a gap. Their S/N of ~20 each would count as an
    # edge event wherever a transit is cut by a gap.
    signal, pg = find_signal(lc, SearchConfig())
    assert signal is not None and signal.detected
    assert signal.period == pytest.approx(period, rel=1e-3)
    assert all(abs(e["time"] - 16.7) > 0.1 for e in pg.edge_events)
