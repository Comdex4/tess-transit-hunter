import math

import numpy as np
import pytest

from transit_hunter.catalog import StellarParams
from transit_hunter.fit import (
    FitConfig,
    TransitFitter,
    derived_samples,
    fit_transit,
    plot_corner,
    plot_fit,
    summarize,
)
from transit_hunter.lightcurve import LightCurve
from transit_hunter.models import (
    TransitParams,
    a_rs_from_density,
    a_rs_from_mass_radius,
    density_solar,
    q_to_u,
    stellar_density,
    t14,
    t23,
    transit_model,
    u_to_q,
)
from transit_hunter.synthetic import tess_timestamps
from transit_hunter.utils import RHO_SUN

TRUTH = TransitParams(t0=2003.2, period=3.7, rp_rs=0.08, a_rs=11.0, b=0.35, u1=0.45, u2=0.2)


def test_limb_darkening_reparameterisation_roundtrip():
    for u1, u2 in [(0.4, 0.2), (0.1, 0.5), (0.7, -0.1)]:
        q1, q2 = u_to_q(u1, u2)
        assert 0 <= q1 <= 1 and 0 <= q2 <= 1
        assert q_to_u(q1, q2) == pytest.approx((u1, u2))


def test_geometry_helpers():
    # The Sun seen by a distant observer: Earth's a/R* and a 13-hour transit.
    a_rs = a_rs_from_mass_radius(365.25, 1.0, 1.0)
    assert a_rs == pytest.approx(215.0, rel=0.01)
    assert t14(365.25, a_rs, 0.00917, 0.0) * 24 == pytest.approx(13.0, rel=0.03)
    assert density_solar(stellar_density(365.25, a_rs)) == pytest.approx(1.0, rel=1e-6)
    assert a_rs_from_density(365.25, RHO_SUN) == pytest.approx(a_rs, rel=1e-9)
    # Grazing geometry has no flat bottom.
    assert t23(3.0, 10.0, 0.1, 0.95) == 0.0
    assert t14(3.0, 10.0, 0.1, 0.95) > 0.0


def _noiseless_lc(params: TransitParams, err_ppm: float = 100.0) -> LightCurve:
    time, sector = tess_timestamps(1, cadence_minutes=2.0, start=2000.0)
    flux = transit_model(time, params)
    return LightCurve(time, flux, np.full(time.size, err_ppm * 1e-6), sector)


@pytest.fixture(scope="module")
def noiseless_fit():
    lc = _noiseless_lc(TRUTH)
    # Start from deliberately imperfect "BLS-like" values.
    config = FitConfig(n_walkers=32, max_steps=3000, min_steps=1500, check_interval=500, seed=3)
    stellar = StellarParams(radius=1.0, radius_err=0.05, teff=5800, teff_err=100)
    return fit_transit(
        lc,
        period=TRUTH.period * (1 + 2e-4),
        t0=TRUTH.t0 + 0.004,
        duration=TRUTH.t14 * 0.9,
        depth=0.8 * TRUTH.rp_rs**2,
        stellar=stellar,
        config=config,
    )


def test_fit_recovers_noiseless_model(noiseless_fit):
    s = noiseless_fit.summary()
    # Epoch: the fitter moves t0 to the transit nearest the data centre.
    n = round((s["t0"]["median"] - TRUTH.t0) / TRUTH.period)
    assert s["t0"]["median"] == pytest.approx(TRUTH.t0 + n * TRUTH.period, abs=20 / 86400)
    assert s["period"]["median"] == pytest.approx(TRUTH.period, rel=2e-5)
    assert s["rp_rs"]["median"] == pytest.approx(TRUTH.rp_rs, rel=0.01)
    assert s["a_rs"]["median"] == pytest.approx(TRUTH.a_rs, rel=0.03)
    assert s["b"]["median"] == pytest.approx(TRUTH.b, abs=0.05)
    assert s["u1"]["median"] == pytest.approx(TRUTH.u1, abs=0.1)
    # Truth lies within the (noise-free, hence narrow) 3-sigma credible range.
    for name, value in (("rp_rs", TRUTH.rp_rs), ("a_rs", TRUTH.a_rs), ("b", TRUTH.b)):
        lo = s[name]["median"] - 3 * s[name]["err_lo"]
        hi = s[name]["median"] + 3 * s[name]["err_hi"]
        assert lo <= value <= hi, name


def test_fit_derived_quantities(noiseless_fit):
    s = noiseless_fit.summary()
    true_rho = density_solar(stellar_density(TRUTH.period, TRUTH.a_rs))
    assert s["rho_star_solar"]["median"] == pytest.approx(true_rho, rel=0.1)
    assert s["t14_hours"]["median"] == pytest.approx(TRUTH.t14 * 24, rel=0.01)
    # R_p = k R*, and the 5 % stellar-radius error dominates the radius uncertainty.
    rp = s["rp_earth"]
    assert rp["median"] == pytest.approx(0.08 * 109.2, rel=0.02)
    assert (rp["err_lo"] + rp["err_hi"]) / 2 / rp["median"] == pytest.approx(0.05, rel=0.2)
    assert "teq_k" in s


def test_fit_report_and_convergence_metadata(noiseless_fit):
    report = noiseless_fit.as_dict()
    assert report["n_samples"] > 500
    assert 0.1 < report["acceptance_fraction"] < 0.8
    assert set(report["autocorr_time"]) == set(noiseless_fit.names)
    assert report["n_points"] == noiseless_fit.fitter.time.size


def test_fit_plots(tmp_path, noiseless_fit):
    for path in (
        plot_fit(noiseless_fit, tmp_path / "fit.png", title="noiseless"),
        plot_corner(noiseless_fit, tmp_path / "corner.png"),
    ):
        assert path.exists() and path.stat().st_size > 20_000


def test_ld_prior_enters_log_prior():
    lc = _noiseless_lc(TRUTH)
    free = TransitFitter(lc, TRUTH.period, TRUTH.t0, TRUTH.t14, TRUTH.rp_rs**2)
    tied = TransitFitter(
        lc,
        TRUTH.period,
        TRUTH.t0,
        TRUTH.t14,
        TRUTH.rp_rs**2,
        FitConfig(ld_prior=(0.2, 0.05, 0.3, 0.05)),
    )
    q1, q2 = u_to_q(0.45, 0.2)
    theta = np.array(
        [
            TRUTH.t0 + 0 * TRUTH.period,
            TRUTH.period,
            TRUTH.rp_rs,
            math.log(TRUTH.a_rs),
            TRUTH.b,
            q1,
            q2,
            1.0,
            math.log(1e-6),
        ]
    )
    theta[0] = free.guess["t0"]
    assert free.log_prior(theta) == 0.0
    expected = -0.5 * (((0.45 - 0.2) / 0.05) ** 2 + ((0.2 - 0.3) / 0.05) ** 2)
    assert tied.log_prior(theta) == pytest.approx(expected)
    # Outside the prior support.
    bad = theta.copy()
    bad[4] = 1.2  # b > 1 + k
    assert not math.isfinite(free.log_prior(bad))


def test_supersampling_is_automatic_for_long_cadence():
    time, _ = tess_timestamps(1, cadence_minutes=30.0)
    lc = LightCurve(time, transit_model(time, TRUTH), np.full(time.size, 1e-4))
    fitter = TransitFitter(lc, TRUTH.period, TRUTH.t0, TRUTH.t14, TRUTH.rp_rs**2)
    assert fitter.supersample == 15
    assert fitter.exp_time == pytest.approx(30 / 1440, rel=1e-3)


def test_summarize_and_radius_without_error():
    s = summarize(np.random.default_rng(0).normal(5.0, 2.0, 200_000))
    assert s["median"] == pytest.approx(5.0, abs=0.02)
    assert s["err_lo"] == pytest.approx(2.0, rel=0.02)
    params = {
        "rp_rs": np.full(10, 0.1),
        "ln_a_rs": np.full(10, math.log(10.0)),
        "b": np.zeros(10),
        "period": np.full(10, 3.0),
        "q1": np.full(10, 0.36),
        "q2": np.full(10, 0.3),
    }
    out = derived_samples(params, StellarParams(radius=0.5))
    assert np.allclose(out["rp_earth"], 0.1 * 0.5 * 109.076, rtol=1e-3)
