"""Selection and bookkeeping of the two real-data calibration scripts (offline)."""

import importlib.util
from pathlib import Path

import pytest

from transit_hunter.catalog import TOI

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tois_script():
    return _load("calibrate_vetting_on_tois")


@pytest.fixture(scope="module")
def fa_script():
    return _load("measure_real_false_alarms")


def _toi(number, period=3.0, tmag=9.0, depth=2000.0, disposition="CP"):
    return TOI(
        toi=number,
        tic_id=int(number * 100),
        disposition=disposition,
        period=period,
        t0_btjd=2000.0,
        duration_hours=2.0,
        depth_ppm=depth,
        rp_earth=5.0,
        tmag=tmag,
        teff=5800.0,
        logg=4.4,
        radius=1.0,
    )


def test_toi_sample_uses_the_candidate_cuts_and_a_seeded_order(tois_script):
    tois = [_toi(100.01 + i) for i in range(20)]
    tois += [_toi(200.01, period=0.8), _toi(201.01, tmag=12.0), _toi(202.01, depth=500.0)]
    order = tois_script.shuffled(tois, seed=1)
    assert len(order) == 20  # the three outside the cuts are gone
    assert [t.toi for t in order] == [t.toi for t in tois_script.shuffled(tois[::-1], seed=1)]
    assert [t.toi for t in order] != sorted(t.toi for t in order)
    assert [t.toi for t in order] != [t.toi for t in tois_script.shuffled(tois, seed=2)]


def _planet(period, verdict="planet candidate (passes all tests)"):
    return {
        "role": "candidate",
        "signal": {"period": period},
        "vetting": {"verdict": verdict, "tests": [{"name": "odd_even", "status": "pass"}]},
    }


def test_detection_is_matched_at_the_period_or_twice_or_half_of_it(tois_script):
    report = {"planets": [_planet(4.0), _planet(10.02)]}
    assert tois_script.match_detection(report, 4.0)[1] == 1.0
    assert tois_script.match_detection(report, 5.0)[1] == 2.0  # a binary found at 2P
    match, ratio = tois_script.match_detection(report, 8.0)
    assert ratio == 0.5 and match["signal"]["period"] == 4.0
    assert tois_script.match_detection(report, 7.0)[0] is None


def test_toi_calibration_summary_counts_verdicts_and_tests(tois_script):
    entries = [
        {"class": "planet", "verdict": "planet candidate (passes all tests)", "tests": {}},
        {
            "class": "false positive",
            "verdict": "likely false positive",
            "tests": {"odd_even": {"status": "fail", "statistic": 9.0}},
        },
        {"class": "false positive", "verdict": "not recovered by the search", "tests": None},
    ]
    summary = tois_script.summarize(entries)
    assert summary["agreement"]["planet"] == {"planet candidate (passes all tests)": 1}
    assert summary["agreement"]["false positive"]["likely false positive"] == 1
    assert summary["tests"]["odd_even"]["false positive"] == {"fail": 1}


def test_false_alarm_summary(fa_script):
    rows = [
        {"n_detections": 0, "top_sde": 5.0, "top_snr": 6.0, "cdpp_1h_ppm": 100.0},
        {"n_detections": 2, "top_sde": 9.0, "top_snr": 12.0, "cdpp_1h_ppm": 300.0},
    ]
    planets = [
        {"tic_id": 2, "verdict": "likely false positive"},
        {"tic_id": 2, "verdict": "planet candidate (with caveats)"},
    ]
    summary = fa_script.summarize(rows, planets)
    assert summary["n_stars"] == 2 and summary["n_with_detection"] == 1
    assert summary["n_stars_with_surviving_candidate"] == 1
    assert summary["verdicts"] == {"likely false positive": 1, "planet candidate (with caveats)": 1}
    assert summary["median_cdpp_1h_ppm"] == 200.0
