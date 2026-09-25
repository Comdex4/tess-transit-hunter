"""The CLI and the end-to-end pipeline, run offline on the synthetic demo system."""

import json

import pytest

from transit_hunter.cli import build_parser, main


def test_parser_run_options():
    args = build_parser().parse_args(
        "run --tic 261136679 --window 1.0 --max-period 30 --quick --sectors 1 4".split()
    )
    assert args.tic == 261136679
    assert args.window == 1.0
    assert args.max_period == 30.0
    assert args.quick and args.sectors == [1, 4]
    with pytest.raises(SystemExit):
        build_parser().parse_args(["run"])  # --tic is required


@pytest.fixture(scope="module")
def demo_report(tmp_path_factory):
    outdir = tmp_path_factory.mktemp("reports")
    argv = "demo --sectors 2 --workers 2 --walkers 24 --max-steps 600 --max-signals 4".split()
    code = main([*argv, "--outdir", str(outdir)])
    assert code == 0
    folder = outdir / "synthetic_demo"
    return folder, json.loads((folder / "report.json").read_text())


def test_demo_writes_complete_report(demo_report):
    folder, report = demo_report
    assert report["target"]["synthetic"] is True
    assert (folder / "summary.md").exists()
    for name in report["figures"].values():
        assert (folder / name).exists(), name
    assert {"detrending", "search_summary", "periodogram_1", "fold_1"} <= set(report["figures"])


def test_demo_recovers_the_synthetic_planets(demo_report):
    _, report = demo_report
    periods = sorted(p["signal"]["period"] for p in report["planets"])
    truth = [3.36, 5.66, 11.38]
    assert len(periods) == 3
    for found, true in zip(periods, truth, strict=True):
        assert found == pytest.approx(true, rel=2e-3)
    for planet in report["planets"]:
        assert "fit" in planet and "vetting" in planet
        assert planet["fit"]["posterior"]["rp_earth"]["median"] > 0
        assert planet["vetting"]["verdict"] != "likely false positive"


@pytest.mark.parametrize(
    ("k_secondary", "expected_roles", "failing_test"),
    [
        # Similar eclipses: BLS reports half the true period; odd and even differ.
        (0.085, ["candidate"], "odd_even"),
        # Much shallower secondary: found at the true period, then its secondary
        # eclipse is found at the same period and phase 0.5.
        (0.055, ["candidate", "secondary"], "secondary"),
    ],
)
def test_pipeline_flags_eclipsing_binaries(tmp_path, k_secondary, expected_roles, failing_test):
    """End to end (no MCMC): both ways an EB can appear are rejected by vetting."""
    from dataclasses import replace

    from transit_hunter.catalog import StellarParams
    from transit_hunter.models import TransitParams, transit_model
    from transit_hunter.pipeline import PipelineConfig, run_on_lightcurve
    from transit_hunter.synthetic import NoiseModel, simulate_lightcurve

    lc = simulate_lightcurve(
        noise=NoiseModel(white_ppm=400, red_ppm=0, rotation_ppm=500), n_sectors=2, seed=66
    )
    primary = TransitParams(2001.0, 5.6, 0.12, 11.0, 0.1, 0.45, 0.2)
    secondary = TransitParams(2001.0 + 2.8, 5.6, k_secondary, 11.0, 0.1, 0.45, 0.2)
    lc = lc.with_flux(lc.flux * transit_model(lc.time, primary) * transit_model(lc.time, secondary))
    config = replace(PipelineConfig(), fit_signals=False)
    config = replace(config, search=replace(config.search, max_signals=3))
    report = run_on_lightcurve(
        lc, tmp_path, StellarParams(radius=1.0, mass=1.0, teff=5800), config, name="EB"
    )
    assert [p["role"] for p in report["planets"]] == expected_roles
    first = report["planets"][0]["vetting"]
    assert first["verdict"] == "likely false positive"
    assert next(t for t in first["tests"] if t["name"] == failing_test)["status"] == "fail"
    if "secondary" in expected_roles:
        assert report["planets"][1]["vetting"]["verdict"].startswith("secondary eclipse")
        assert "(not a planet)" in (tmp_path / "summary.md").read_text()


def test_summary_lists_skipped_peaks():
    from transit_hunter.pipeline import render_summary

    signal = {
        "iteration": 1,
        "period": 4.0,
        "t0": 2001.0,
        "duration": 0.1,
        "depth": 1e-4,
        "snr": 5.0,
        "sde": 6.0,
        "detected": False,
        "harmonic_of": None,
        "secondary_of": None,
        "skipped_peaks": [{"period": 12.03, "sde": 7.7, "reason": "sinusoid-like: variability"}],
    }
    report = {
        "target": {"name": "x", "sectors": [1], "n_points": 10, "baseline_days": 27.0},
        "noise": {"robust_cdpp_ppm": {"1h": 100.0}},
        "search": {"signals": [signal]},
        "planets": [],
        "figures": {},
    }
    text = render_summary(report)
    assert "* iteration 1: P = 12.03000 d, SDE 7.7: sinusoid-like: variability" in text


def test_network_errors_give_a_clear_message(monkeypatch, capsys, tmp_path):
    import requests

    import transit_hunter.data as data

    def unreachable(*args, **kwargs):
        raise requests.exceptions.ProxyError("Tunnel connection failed: 403 Forbidden")

    monkeypatch.setattr(data, "download_spoc_sectors", unreachable)
    code = main(["fetch", "--tic", "1", "--cache-dir", str(tmp_path)])
    assert code == 2
    assert "mast.stsci.edu" in capsys.readouterr().err
