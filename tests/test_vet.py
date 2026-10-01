import numpy as np
import pytest

from transit_hunter.catalog import StellarParams
from transit_hunter.lightcurve import LightCurve
from transit_hunter.models import TransitParams, transit_model
from transit_hunter.synthetic import tess_timestamps
from transit_hunter.utils import fold
from transit_hunter.vet import (
    FAIL,
    NA,
    PASS,
    WARN,
    TestResult,
    VetConfig,
    bad_transits,
    coverage_test,
    decide,
    density_tension,
    density_test,
    dropped_transits_note,
    fit_trapezoid,
    max_planet_occultation,
    measure_transit_times,
    momentum_dump_test,
    noise_properties,
    odd_even_test,
    plot_vetting,
    radius_test,
    rotation_period,
    rotation_test,
    run_vetting,
    secondary_eclipse_test,
    shape_test,
    template_from_params,
    transit_coverage,
    transit_depths,
    trapezoid,
    without_transits,
)

P = 2.8
T0 = 2001.3


def _lc(flux_model: np.ndarray, time: np.ndarray, noise_ppm: float, seed: int) -> LightCurve:
    rng = np.random.default_rng(seed)
    flux = flux_model + rng.normal(0, noise_ppm * 1e-6, time.size)
    return LightCurve(time, flux, np.full(time.size, noise_ppm * 1e-6))


@pytest.fixture(scope="module")
def time():
    return tess_timestamps(2, cadence_minutes=2.0)[0]


@pytest.fixture(scope="module")
def planet_lc(time):
    """A clean hot-Neptune transit (no secondary, U-shaped)."""
    params = TransitParams(T0, P, 0.06, 9.0, 0.2, 0.4, 0.2)
    return _lc(transit_model(time, params), time, 400, seed=1), params


@pytest.fixture(scope="module")
def eb_half_period_lc(time):
    """An EB found at half its period: alternating eclipse depths of ~1.1 % and ~0.6 %."""
    primary = TransitParams(T0, 2 * P, 0.10, 12.0, 0.1, 0.4, 0.2)
    secondary = TransitParams(T0 + P, 2 * P, 0.075, 12.0, 0.1, 0.4, 0.2)
    flux = transit_model(time, primary) * transit_model(time, secondary)
    return _lc(flux, time, 400, seed=2), primary


def test_trapezoid_shapes():
    t = np.linspace(-0.1, 0.1, 2001)
    box = trapezoid(t, 0.0, 0.01, 0.1, 0.01)
    vee = trapezoid(t, 0.0, 0.01, 0.1, 1.0)
    assert box.min() == pytest.approx(0.99) and vee.min() == pytest.approx(0.99, abs=2e-5)
    # A V has half the area of a box of equal depth and duration.
    assert (1 - vee).sum() == pytest.approx(0.5 * (1 - box).sum(), rel=0.03)


def test_odd_even_passes_planet_and_fails_eb(planet_lc, eb_half_period_lc):
    lc, params = planet_lc
    planet = odd_even_test(lc, P, T0, params.t14)
    assert planet.status == PASS
    assert planet.statistic < 3

    eb, primary = eb_half_period_lc
    result = odd_even_test(eb, P, T0, primary.t14)
    assert result.status == FAIL
    assert result.statistic > 10
    # Epoch 0 (the deeper eclipse) is "even".
    assert result.details["even"]["depth"] > result.details["odd"]["depth"]


def test_secondary_eclipse_of_eclipsing_binary_fails(time):
    primary = TransitParams(T0, P, 0.15, 8.0, 0.1, 0.4, 0.2)
    occultation = TransitParams(T0 + P / 2, P, 0.07, 8.0, 0.1, 0.0, 0.0)  # ~0.5 % deep
    flux = transit_model(time, primary) * transit_model(time, occultation)
    lc = _lc(flux, time, 500, seed=3)
    result = secondary_eclipse_test(lc, P, T0, primary.t14, rp_rs=0.15, a_rs=8.0, teff=5800)
    assert result.status == FAIL
    assert result.details["depth"] == pytest.approx(0.07**2, rel=0.15)
    assert result.details["depth"] > 2 * result.details["max_planet_depth"]
    assert abs(result.details["scan_phase"] - 0.5) < 0.02


def test_secondary_eclipse_of_hot_planet_is_acceptable(time):
    # Hot Jupiter: 300 ppm occultation, which a planet at a/R* = 3.5 can produce.
    primary = TransitParams(T0, P, 0.1, 3.5, 0.3, 0.4, 0.2)
    occultation = TransitParams(T0 + P / 2, P, np.sqrt(300e-6), 3.5, 0.3, 0.0, 0.0)
    flux = transit_model(time, primary) * transit_model(time, occultation)
    lc = _lc(flux, time, 150, seed=4)
    limit = max_planet_occultation(0.1, 3.5, 6400)
    assert limit > 600e-6
    result = secondary_eclipse_test(lc, P, T0, primary.t14, rp_rs=0.1, a_rs=3.5, teff=6400)
    assert result.statistic > 3  # detected ...
    assert result.status == PASS  # ... but consistent with a planet
    # Without a fit there is nothing to compare with: warn.
    assert secondary_eclipse_test(lc, P, T0, primary.t14).status == WARN


def test_no_secondary_passes(planet_lc):
    lc, params = planet_lc
    result = secondary_eclipse_test(lc, P, T0, params.t14, rp_rs=0.06, a_rs=9.0, teff=5800)
    assert result.status == PASS
    assert abs(result.statistic) < 3


def test_shape_distinguishes_u_from_v(planet_lc, time):
    lc, params = planet_lc
    u = shape_test(lc, P, T0, params.t14)
    assert u.status == PASS and u.statistic < 0.5

    grazing = TransitParams(T0, P, 0.3, 6.0, 1.1, 0.4, 0.2)
    v_lc = _lc(transit_model(time, grazing), time, 300, seed=5)
    v = shape_test(
        v_lc, P, T0, grazing.t14, b_samples=np.full(100, 1.1), k_samples=np.full(100, 0.3)
    )
    assert v.status == WARN
    # A grazing profile is rounded rather than triangular, but far more V-like than
    # the planet's.
    assert v.statistic > 0.7 > 0.5 > u.statistic
    assert v.details["p_grazing"] == 1.0


def test_trapezoid_fit_recovers_duration(planet_lc):
    lc, params = planet_lc
    trap = fit_trapezoid(lc, P, T0, params.t14)
    assert trap["t14"] == pytest.approx(params.t14, rel=0.1)
    assert trap["depth"] == pytest.approx(0.06**2, rel=0.25)


def test_density_test_outcomes():
    rng = np.random.default_rng(6)
    samples = np.exp(rng.normal(np.log(1.0), 0.05, 5000))
    assert density_test(samples, StellarParams(density=1.05, density_err=0.1)).status == PASS
    assert density_test(samples, StellarParams(density=2.0, density_err=0.1)).status == WARN
    assert density_test(samples, StellarParams(density=10.0, density_err=1.0)).status == FAIL
    # Density derived from mass and radius when the catalogue has no rho.
    derived = density_test(
        samples, StellarParams(mass=1.0, mass_err=0.05, radius=1.0, radius_err=0.03)
    )
    assert derived.status == PASS
    assert density_test(samples, None).status == NA


def test_density_tension_reduces_to_the_log_normal_formula():
    # For a log-normal posterior the tail probability gives back the difference of the
    # log densities over their combined width, with its sign.
    rng = np.random.default_rng(7)
    log_fit = rng.normal(0.0, 0.2, 20000)
    for rho_cat, sd_cat in ((1.5, 0.1), (3.0, 0.25), (0.5, 0.2)):
        expected = -np.log(rho_cat) / np.hypot(0.2, sd_cat)
        tension = density_tension(log_fit, np.log(rho_cat), sd_cat)
        assert tension == pytest.approx(expected, abs=0.05)


def test_density_mismatch_is_not_diluted_by_a_second_posterior_mode():
    # L 98-59's 1.049-day binary: the fit wanders between a non-grazing solution near
    # 0.9 rho_sun and a grazing one near 0.04 rho_sun. No sample comes within a factor
    # of 5 of the catalogue's 9.44 rho_sun, but half the 16-84 % range of the log
    # density, which the test used to divide by, spans both modes.
    rng = np.random.default_rng(8)
    log_s = np.r_[rng.normal(np.log(0.9), 0.2, 1400), rng.normal(np.log(0.04), 0.4, 600)]
    half_range = 0.5 * (np.percentile(log_s, 84.135) - np.percentile(log_s, 15.865))
    old_z = (np.median(log_s) - np.log(9.44)) / np.hypot(half_range, 0.5 / 9.44)
    assert abs(old_z) < 3  # the old statistic let it pass

    result = density_test(np.exp(log_s), StellarParams(density=9.44, density_err=0.5))
    assert result.status == FAIL
    assert result.statistic < -5


def test_radius_test():
    star = StellarParams(radius=1.0)
    assert radius_test(np.full(10, 0.1), star).status == PASS
    assert radius_test(np.full(10, 0.5), star).status == FAIL
    assert radius_test(np.full(10, 0.1), None).status == NA


def test_decide_combines_tests():
    ok = TestResult("a", PASS, 0, "fine")
    warn = TestResult("b", WARN, 0, "hmm")
    bad = TestResult("c", FAIL, 0, "no")
    assert decide([ok, ok])[0] == "planet candidate (passes all tests)"
    assert decide([ok, warn])[0] == "planet candidate (with caveats)"
    verdict, reasons = decide([ok, warn, bad])
    assert verdict == "likely false positive"
    assert len(reasons) == 3 and reasons[2].startswith("[fail] c")


def test_decide_counts_tests_that_could_not_run_as_caveats():
    ok = TestResult("odd_even", PASS, 0, "fine")
    no_radius = TestResult("radius", NA, float("nan"), "no stellar radius")
    verdict, reasons = decide([ok, no_radius])
    assert verdict == "planet candidate (with caveats)"
    assert reasons[-1] == "not tested: radius, so the verdict rests on the other tests"
    # No rotational modulation is itself the answer to the rotation test.
    no_rotation = TestResult("rotation", NA, float("nan"), "no clear rotational modulation")
    assert decide([ok, no_rotation])[0] == "planet candidate (passes all tests)"
    assert decide([no_radius, TestResult("x", FAIL, 0, "no")])[0] == "likely false positive"


def test_run_vetting_without_fit_and_plot(tmp_path, eb_half_period_lc):
    eb, primary = eb_half_period_lc
    report = run_vetting(eb, P, T0, primary.t14, stellar=StellarParams(radius=1.0, teff=5800))
    assert report.verdict == "likely false positive"
    assert report.test("odd_even").status == FAIL
    assert report.test("density").status == NA
    path = plot_vetting(eb, P, T0, primary.t14, report, tmp_path / "vet.png", title="EB")
    assert path.exists() and path.stat().st_size > 20_000
    assert set(report.as_dict()) == {"verdict", "reasons", "tests"}


def test_secondary_scan_catches_eccentric_eb(time):
    primary = TransitParams(T0, P, 0.15, 8.0, 0.1, 0.4, 0.2)
    # Secondary eclipse at phase 0.35 (eccentric orbit), 0.5 % deep.
    occultation = TransitParams(T0 + 0.35 * P, P, 0.07, 8.0, 0.1, 0.0, 0.0)
    flux = transit_model(time, primary) * transit_model(time, occultation)
    lc = _lc(flux, time, 500, seed=8)
    result = secondary_eclipse_test(lc, P, T0, primary.t14, rp_rs=0.15, a_rs=8.0, teff=5800)
    assert result.status == FAIL
    assert result.details["scan_phase"] == pytest.approx(0.35, abs=0.02)
    assert "eccentric" in result.message


def test_run_vetting_without_fit_estimates_planet_limit(time):
    """Without an MCMC fit the occultation limit comes from the BLS depth and duration."""
    primary = TransitParams(T0, P, 0.15, 8.0, 0.1, 0.4, 0.2)
    occultation = TransitParams(T0 + P / 2, P, 0.07, 8.0, 0.1, 0.0, 0.0)
    lc = _lc(transit_model(time, primary) * transit_model(time, occultation), time, 500, seed=9)
    report = run_vetting(
        lc, P, T0, primary.t14, stellar=StellarParams(radius=1.0, teff=5800), depth=0.15**2
    )
    assert report.test("secondary").status == FAIL
    assert report.verdict == "likely false positive"


def test_rotation_period_is_recovered_with_transits_masked():
    from transit_hunter.detrend import ephemeris_mask
    from transit_hunter.synthetic import NoiseModel, SyntheticStar, simulate_lightcurve

    noise = NoiseModel(white_ppm=800, red_ppm=80, rotation_ppm=2000, rotation_period=7.0)
    star = SyntheticStar()
    lc = simulate_lightcurve(star, noise, n_sectors=3, seed=5)
    rot = rotation_period(lc)
    assert rot["period"] == pytest.approx(7.0, rel=0.05)
    assert rot["power"] > 0.3 and rot["amplitude_ppm"] > 500
    # On a quiet star a planet's own transits set the periodogram's peak (at a harmonic
    # of the orbit) unless they are masked.
    quiet = NoiseModel(white_ppm=300, red_ppm=0, rotation_ppm=0)
    planet = TransitParams(2001.0, 3.1, 0.12, 9.0, 0.2, 0.4, 0.2)
    base = simulate_lightcurve(star, quiet, n_sectors=2, seed=6)
    lc = base.with_flux(base.flux * transit_model(base.time, planet))
    harmonic = planet.period / rotation_period(lc)["period"]
    assert harmonic == pytest.approx(round(harmonic), abs=0.02)
    masked = ephemeris_mask(lc.time, [(planet.period, planet.t0, planet.t14)])
    assert rotation_period(lc, masked)["power"] < 0.02


def test_rotation_test_warns_near_rotation_harmonics():
    rotation = {"period": 7.0, "power": 0.6, "amplitude_ppm": 1500.0}
    for period in (7.1, 3.45, 14.2):
        assert rotation_test(period, rotation).status == WARN
    assert rotation_test(5.0, rotation).status == PASS
    assert rotation_test(3.5, {**rotation, "power": 0.05}).status == NA
    assert rotation_test(3.5, None).status == NA


def test_coverage_test_fails_signals_made_of_edge_events():
    t = np.concatenate([np.arange(0.0, 10.0, 2 / 1440), np.arange(20.0, 30.0, 2 / 1440)])
    lc = LightCurve(t, np.ones(t.size), np.full(t.size, 1e-3))
    # Transits 0.05 d after one segment starts and 0.05 d before the other ends.
    assert coverage_test(lc, 29.9, 0.05, 0.12).status == FAIL
    assert coverage_test(lc, 3.1, 1.0, 0.12).status == PASS
    single = coverage_test(lc, 25.9, 4.0, 0.12)  # the second transit is 0.1 d before the end
    assert single.status == WARN and single.details["n_fully_covered"] == 1


def _ttv_light_curve(amplitude_min: float, seed: int) -> tuple[LightCurve, TransitParams]:
    """Transits whose mid-times oscillate by ``amplitude_min`` over eight orbits."""
    params = TransitParams(2000.5, 3.0, 0.05, 12.0, 0.2, 0.4, 0.2)
    t = tess_timestamps(2, cadence_minutes=2.0)[0]
    n = np.round((t - params.t0) / params.period)
    shift = amplitude_min / 1440 * np.sin(2 * np.pi * n / 8)
    return _lc(transit_model(t - shift, params), t, 300, seed), params


def test_transit_times_recover_injected_ttvs():
    lc, params = _ttv_light_curve(12.0, seed=31)
    epochs = transit_coverage(lc, params.period, params.t0, params.t14)
    times = measure_transit_times(
        lc, params.period, params.t0, params.t14, template_from_params(params), epochs
    )
    assert len(times) > 10
    measured = np.array([(x["tc"] - params.t0 - x["epoch"] * params.period) * 1440 for x in times])
    injected = np.array([12.0 * np.sin(2 * np.pi * x["epoch"] / 8) for x in times])
    errors = np.array([x["err"] * 1440 for x in times])
    assert np.all(errors < 3.0)
    assert np.sqrt(np.mean((measured - injected) ** 2)) < 2.0  # minutes


def _varying_depths_lc(time, scatter, seed, noise_ppm=100):
    """A deep transit whose depth changes from transit to transit by ``scatter`` (relative)."""
    params = TransitParams(T0, P, 0.1, 9.0, 0.2, 0.4, 0.2)
    rng = np.random.default_rng(seed)
    epochs = np.round((time - T0) / P).astype(int)
    factor = 1.0 + scatter * rng.normal(size=epochs.max() - epochs.min() + 1)
    dip = 1.0 - transit_model(time, params)
    return _lc(1.0 - dip * factor[epochs - epochs.min()], time, noise_ppm, seed), params


def test_odd_even_uncertainty_includes_scatter_between_transits(time, eb_half_period_lc):
    # At S/N ~ 100 per transit, 3 % depth variations between transits look like a
    # significant odd/even difference if only the white noise is counted.
    lc, params = _varying_depths_lc(time, 0.03, seed=40)
    unfloored = odd_even_test(lc, P, T0, params.t14, config=VetConfig(odd_even_min_per_parity=99))
    assert unfloored.status == FAIL and not unfloored.details["scatter_floor_applied"]
    result = odd_even_test(lc, P, T0, params.t14)
    assert result.details["scatter_floor_applied"]
    assert result.details["transit_scatter"] == pytest.approx(0.03 * 0.01, rel=0.5)
    assert result.status == PASS
    assert "scatter between transits" in result.message
    # The scatter is taken within each parity, so an EB's alternating depths still fail.
    eb, primary = eb_half_period_lc
    eb_result = odd_even_test(eb, P, T0, primary.t14)
    assert eb_result.status == FAIL and eb_result.statistic > 10


def test_odd_even_measures_each_transit_against_its_surroundings(planet_lc):
    # A detrending residual lowers the flux by 300 ppm around every odd transit.
    # Against one global baseline those transits would look 300 ppm deeper.
    lc, params = planet_lc
    offset = np.abs(fold(lc.time, P, T0)) < 1.5 * params.t14
    odd = np.round((lc.time - T0) / P).astype(int) % 2 == 1
    shifted = lc.with_flux(lc.flux - 300e-6 * (offset & odd))
    result = odd_even_test(shifted, P, T0, params.t14)
    assert result.status == PASS
    assert abs(result.details["difference"]) < 3 * result.details["difference_err"]


def _with_dip(lc, centre, width, depth):
    return lc.with_flux(lc.flux - depth * (np.abs(lc.time - centre) < width / 2))


def test_secondary_dips_from_a_single_orbit_are_not_counted(planet_lc):
    lc, params = planet_lc
    width = params.t14
    # One instrumental dip at phase 0.5 of one orbit only, 2000 ppm deep.
    one_orbit = _with_dip(lc, T0 + 3.5 * P, width, 2000e-6)
    result = secondary_eclipse_test(one_orbit, P, T0, width, rp_rs=0.06, a_rs=9.0, teff=5800)
    assert result.statistic > 3  # the averaged phase-0.5 box is still significant ...
    assert result.status == PASS  # ... but it comes from one orbit
    assert "single orbit" in result.message
    assert result.details["snr_without_strongest_orbit"] < 3
    # The same at phase 0.3: reported, not counted.
    scan = _with_dip(lc, T0 + 1.3 * P, width, 3000e-6)
    result = secondary_eclipse_test(scan, P, T0, width, rp_rs=0.06, a_rs=9.0, teff=5800)
    assert result.status == PASS
    dips = result.details["scan_single_orbit_dips"]
    assert dips and dips[0]["phase"] == pytest.approx(0.3, abs=0.02)
    # A dip at phase 0.5 of every orbit is a real eclipse and still fails.
    eclipse = TransitParams(T0 + P / 2, P, 0.045, 9.0, 0.2, 0.0, 0.0)
    real = lc.with_flux(lc.flux * transit_model(lc.time, eclipse))
    result = secondary_eclipse_test(real, P, T0, width, rp_rs=0.06, a_rs=9.0, teff=5800)
    assert result.status == FAIL
    assert result.details["snr_without_strongest_orbit"] > 3


def test_bad_transits_flags_a_single_transit_on_a_ramp(planet_lc):
    lc, params = planet_lc
    width = params.t14
    depths = transit_depths(lc, P, T0, width)
    assert len(depths) >= 15
    assert np.median([d["depth"] for d in depths]) == pytest.approx(0.06**2, rel=0.25)
    assert bad_transits(lc, P, T0, width)[0] == []
    # One transit sits on an instrumental ramp: 3000 ppm deeper, with the level stepping down.
    tc = T0 + 5 * P
    ramp = np.clip((lc.time - (tc - 2 * width)) / (4 * width), 0.0, 1.0) * (
        np.abs(lc.time - tc) < 2 * width
    )
    bad = lc.with_flux(lc.flux - 3000e-6 * (np.abs(lc.time - tc) < width / 2) - 2000e-6 * ramp)
    flagged, stats = bad_transits(bad, P, T0, width)
    assert [round(x["tc"], 6) for x in flagged] == [round(tc, 6)]
    assert flagged[0]["deviation"] > 5 and flagged[0]["step"] > 1000e-6
    assert stats["n_measured"] == len(depths)
    rest = without_transits(bad, [x["tc"] for x in flagged], width)
    assert len(rest) < len(bad) and bad_transits(rest, P, T0, width)[0] == []
    note = dropped_transits_note(flagged, stats)
    assert note.startswith("[note] left out before the fit and the tests")
    assert f"BTJD {tc:.3f}" in note
    # With too few transits nothing is judged.
    assert bad_transits(bad, P, T0, width, VetConfig(bad_transit_min_count=100))[0] == []
    # A transit cut by a gap is measured against the flank it has.
    cut = bad.select(bad.time < tc + 0.3 * width)
    flagged, _ = bad_transits(cut, P, T0, width)
    assert [round(x["tc"], 6) for x in flagged] == [round(tc, 6)]
    assert flagged[0]["sides"] == 1 and "data on one side only" in dropped_transits_note(
        flagged, stats
    )


def test_bad_transits_leaves_an_eclipsing_binary_alone(eb_half_period_lc):
    # Found at half its period, a binary's primary and secondary eclipses form two
    # groups of depths. One whole group stands out from the other, which is no
    # stray transit, so nothing is dropped and the odd/even test still sees it.
    eb, primary = eb_half_period_lc
    flagged, stats = bad_transits(eb, P, T0, primary.t14)
    assert flagged == []
    # With equal groups the scatter spans both; with unequal ones a whole group
    # stands out. Neither looks like a stray transit.
    assert stats["scatter"] > 1000e-6 or stats["n_standing_out"] >= 0.4 * stats["n_measured"]


def test_noise_is_measured_even_for_a_signal_lasting_a_quarter_of_the_orbit(planet_lc):
    # A 9-hour "transit" every 1.27 days leaves nothing clear of both eclipse
    # windows; the tests must still see a finite noise level.
    lc, _ = planet_lc
    sigma, beta = noise_properties(lc, 1.27, T0, 9.2 / 24)
    assert np.isfinite(sigma) and sigma > 0 and np.isfinite(beta)
    assert odd_even_test(lc, 1.27, T0, 9.2 / 24).status != NA
    result = secondary_eclipse_test(lc, 1.27, T0, 9.2 / 24, rp_rs=0.01, a_rs=1.3, teff=6000)
    assert np.isfinite(result.details["depth_err"])


# Momentum dumps: 60 days of 2-minute data, a 12-day "period" with epochs at
# BTJD 1402, 1414, 1426, 1438 and 1450, and dumps every 2.5 days well away from
# them unless placed at chosen epochs.
DUMP_P, DUMP_T0, DUMP_DURATION = 12.0, 1402.0, 1.8 / 24
FILLER_DUMPS = [
    t
    for t in 1403.25 + 2.5 * np.arange(23)
    if min(abs(t - (DUMP_T0 + DUMP_P * e)) for e in range(5)) > 0.2
]


def _dump_lc(dips: dict[int, float], dumps_at: list[int], seed: int = 3) -> LightCurve:
    """Box dips of the given depth at the given epochs, and dumps at ``dumps_at``."""
    time = 1400.0 + np.arange(0, 60, 2 / 1440)
    flux = np.ones(time.size)
    for epoch, depth in dips.items():
        flux[np.abs(time - (DUMP_T0 + DUMP_P * epoch)) < DUMP_DURATION / 2] -= depth
    lc = _lc(flux, time, 1000, seed)
    at = [DUMP_T0 + DUMP_P * e + 0.02 for e in dumps_at]  # half an hour after mid-transit
    lc.meta["momentum_dumps"] = sorted(FILLER_DUMPS + at)
    return lc


def test_momentum_dumps_fail_dips_made_at_dumps():
    # The 12.03-day signal of TIC 100103201: the dip is at the three epochs with a
    # dump, and the two others are flat.
    lc = _dump_lc({1: 2000e-6, 2: 2000e-6, 4: 2000e-6}, dumps_at=[1, 2, 4])
    result = momentum_dump_test(lc, DUMP_P, DUMP_T0, DUMP_DURATION)
    assert result.status == FAIL
    assert "3 of 5 transits" in result.message and "the dip comes from the dumps" in result.message
    assert result.details["at_dump_tc"] == [1414.0, 1426.0, 1450.0]


def test_momentum_dumps_pass_a_planet_whose_transits_meet_dumps_by_chance():
    planet = dict.fromkeys(range(5), 2000e-6)
    result = momentum_dump_test(_dump_lc(planet, dumps_at=[1, 3]), DUMP_P, DUMP_T0, DUMP_DURATION)
    assert result.status == PASS and "2 of 5 transits" in result.message
    result = momentum_dump_test(_dump_lc(planet, dumps_at=[]), DUMP_P, DUMP_T0, DUMP_DURATION)
    assert result.status == PASS and result.message.startswith("no transit within 1 h")


def test_momentum_dumps_warn_when_transits_at_dumps_are_only_deeper():
    # A real dip everywhere, made deeper by the dumps at two epochs.
    dips = dict.fromkeys(range(5), 2000e-6) | {1: 4000e-6, 3: 4000e-6}
    result = momentum_dump_test(_dump_lc(dips, dumps_at=[1, 3]), DUMP_P, DUMP_T0, DUMP_DURATION)
    assert result.status == WARN and "deeper at the dumps" in result.message


def test_momentum_dumps_every_transit_at_a_dump():
    lc = _dump_lc(dict.fromkeys(range(5), 2000e-6), dumps_at=list(range(5)))
    result = momentum_dump_test(lc, DUMP_P, DUMP_T0, DUMP_DURATION)
    assert result.status == FAIL and result.message.startswith("all 5 transits")
    assert result.statistic < 1e-4  # ~6 % of the data lie near a dump; to the 5th power
    one = lc.select(lc.time < 1410)  # a single transit, at a dump: possible by chance
    result = momentum_dump_test(one, DUMP_P, DUMP_T0, DUMP_DURATION)
    assert result.status == WARN and result.message.startswith("the only transit")


def test_momentum_dump_test_needs_the_dump_times(planet_lc):
    lc, params = planet_lc  # simulated, so without dump times
    assert "momentum_dumps" not in lc.meta
    assert momentum_dump_test(lc, P, T0, params.t14) is None
    report = run_vetting(lc, P, T0, params.t14, depth=params.rp_rs**2)
    assert "momentum_dumps" not in [t.name for t in report.tests]
    with_dumps = lc.with_flux(lc.flux, momentum_dumps=[])
    report = run_vetting(with_dumps, P, T0, params.t14, depth=params.rp_rs**2)
    assert report.test("momentum_dumps").status == PASS
