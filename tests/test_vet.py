import numpy as np
import pytest

from transit_hunter.catalog import StellarParams
from transit_hunter.lightcurve import LightCurve
from transit_hunter.models import TransitParams, transit_model
from transit_hunter.synthetic import tess_timestamps
from transit_hunter.vet import (
    FAIL,
    NA,
    PASS,
    WARN,
    TestResult,
    decide,
    density_test,
    fit_trapezoid,
    max_planet_occultation,
    odd_even_test,
    plot_vetting,
    radius_test,
    run_vetting,
    secondary_eclipse_test,
    shape_test,
    trapezoid,
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
