"""Offline tests of archive-table parsing and of the validation comparison."""

import math

import numpy as np
import pytest

from transit_hunter.catalog import (
    RHO_SUN_CGS,
    PublishedPlanet,
    StellarParams,
    parse_tic_id,
    planet_from_archive_row,
    stellar_params_from_tic_row,
    symmetric_error,
    to_float,
    toi_from_row,
)
from transit_hunter.validation import (
    compare_planet,
    comparison_markdown,
    pct_error,
    plot_comparison,
)


def test_to_float_handles_masked_and_bad_values():
    assert to_float(np.float32(2.5)) == 2.5
    assert to_float(np.ma.masked) is None
    assert to_float("n/a") is None
    assert to_float(float("nan")) is None
    assert to_float(None) is None
    assert symmetric_error(0.1, -0.3) == pytest.approx(0.2)
    assert symmetric_error(None, np.ma.masked) is None


def test_parse_tic_id():
    assert parse_tic_id("TIC 261136679") == 261136679
    assert parse_tic_id(307210830) == 307210830
    assert parse_tic_id("  12 ") == 12
    assert parse_tic_id(None) is None
    assert parse_tic_id("unknown") is None


def test_stellar_density_fallbacks():
    assert StellarParams(density=2.0, density_err=0.2).density_solar() == (2.0, 0.2)
    rho, err = StellarParams(mass=0.5, mass_err=0.05, radius=0.5, radius_err=0.01).density_solar()
    assert rho == pytest.approx(4.0)
    assert err == pytest.approx(4.0 * math.hypot(0.1, 0.06))
    rho, _ = StellarParams(logg=4.438, radius=1.0).density_solar()
    assert rho == pytest.approx(1.0, rel=1e-3)
    assert StellarParams().density_solar() == (None, None)


def test_tic_row_parsing():
    row = {
        "rad": 0.3,
        "e_rad": 0.01,
        "mass": 0.29,
        "e_mass": 0.02,
        "rho": 10.7,
        "e_rho": 1.1,
        "Teff": 3400,
        "e_Teff": 157,
        "logg": 4.9,
        "e_logg": 0.01,
        "Tmag": 7.9,
    }
    star = stellar_params_from_tic_row(row)
    assert star.radius == 0.3 and star.density == 10.7 and star.teff == 3400
    assert "TIC" in star.source
    # Missing columns are tolerated.
    assert stellar_params_from_tic_row({"rad": 1.0}).mass is None


def test_archive_row_parsing_units():
    row = {
        "pl_name": "Test b",
        "hostname": "Test",
        "tic_id": "TIC 42",
        "pl_orbper": 3.5,
        "pl_orbpererr1": 1e-5,
        "pl_orbpererr2": -1e-5,
        "pl_tranmid": 2459000.5,
        "pl_trandep": 0.25,
        "pl_ratror": 0.05,
        "pl_rade": 2.2,
        "pl_radeerr1": 0.1,
        "pl_radeerr2": -0.2,
        "st_rad": 0.8,
        "st_dens": 2.0,
        "st_denserr1": 0.2,
        "st_denserr2": -0.2,
        "st_teff": 5000,
    }
    planet = planet_from_archive_row(row)
    assert planet.tic_id == 42
    assert planet.t0_btjd == pytest.approx(2000.5)  # BJD - 2457000
    assert planet.depth_ppm == pytest.approx(2500.0)  # 0.25 % -> ppm
    assert planet.rp_earth_err == pytest.approx(0.15)
    assert planet.stellar.density == pytest.approx(2.0 / RHO_SUN_CGS)  # g/cm^3 -> solar
    assert RHO_SUN_CGS == pytest.approx(1.41, abs=0.01)


def test_toi_row_parsing():
    toi = toi_from_row(
        {
            "toi": 175.01,
            "tid": 307210830,
            "tfopwg_disp": "PC ",
            "pl_orbper": 3.69,
            "pl_tranmid": 2458366.17,
            "pl_trandep": 1500.0,
            "st_tmag": 7.9,
        }
    )
    assert toi.name == "TOI-175.01"
    assert toi.disposition == "PC"
    assert toi.t0_btjd == pytest.approx(1366.17)
    assert toi.depth_ppm == 1500.0


def _published(period=3.0, k=0.05, rp=2.0):
    return PublishedPlanet(
        name="Test b",
        host="Test",
        tic_id=1,
        period=period,
        period_err=1e-5,
        t0_btjd=2000.0,
        depth_ppm=None,
        duration_hours=2.0,
        rp_rs=k,
        rp_rs_err=0.001,
        rp_earth=rp,
        rp_earth_err=0.1,
        a_rs=10.0,
        impact=0.3,
        stellar=StellarParams(radius=0.4),
    )


def _post(median, err=0.01):
    return {"median": median, "err_lo": err, "err_hi": err}


def _report(period=3.0003):
    return {
        "planets": [
            {
                "signal": {
                    "period": period,
                    "sde": 12.0,
                    "snr": 25.0,
                    "depth": 0.0024,
                    "detected": True,
                },
                "fit": {
                    "posterior": {
                        "period": _post(period, 1e-5),
                        "rp_rs": _post(0.051),
                        "depth_ppm": _post(2601.0, 50),
                        "rp_earth": _post(2.1, 0.1),
                    },
                    "converged": True,
                },
                "vetting": {"verdict": "planet candidate (passes all tests)"},
            }
        ],
        "search": {"signals": []},
    }


def test_compare_planet_recovered():
    row = compare_planet(_published(), _report())
    assert row["recovered"]
    assert row["depth_pub_kind"] == "(Rp/R*)^2"
    assert row["depth_pub_ppm"] == pytest.approx(2500.0)
    assert row["depth_pct"] == pytest.approx(100 * (2601 - 2500) / 2500)
    assert row["period_pct"] == pytest.approx(0.01)
    assert row["rp_pct"] == pytest.approx(5.0)
    assert row["verdict"].startswith("planet candidate")


def test_compare_planet_not_recovered_reports_subthreshold_peak():
    report = {
        "planets": [],
        "search": {"signals": [{"period": 7.001, "detected": False, "sde": 5.0, "snr": 5.5}]},
    }
    row = compare_planet(_published(period=7.0), report)
    assert not row["recovered"]
    assert row["found_below_threshold"]
    table = comparison_markdown([row, compare_planet(_published(), _report())])
    assert "not recovered (peak below threshold: S/N 5.5, SDE 5.0)" in table
    assert "+4.0%" in table  # depth error of the recovered planet (4.04 %)


def test_pct_error_edge_cases():
    assert pct_error(None, 1.0) is None
    assert pct_error(1.0, 0.0) is None
    assert pct_error(1.1, 1.0) == pytest.approx(10.0)


def test_plot_comparison(tmp_path):
    rows = [compare_planet(_published(), _report())]
    path = plot_comparison(rows, tmp_path / "cmp.png")
    assert path.exists() and path.stat().st_size > 5_000


def test_toi_row_accepts_alternative_tic_column():
    toi = toi_from_row({"toi": 700.01, "tic_id": "TIC 150428135", "tfopwg_disp": "PC"})
    assert toi.tic_id == 150428135
    assert toi.period is None  # missing columns become None rather than failing


def test_known_ephemerides_skip_incomplete_rows():
    from transit_hunter.catalog import known_ephemerides

    complete = _published(period=3.0)
    incomplete = _published(period=5.0)
    incomplete.duration_hours = None
    assert known_ephemerides([complete, incomplete]) == [(3.0, 2000.0, 2.0 / 24.0)]
