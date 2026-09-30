"""Batch search: target lists, catalogue matches, screening, the runner and its tables."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import replace

import numpy as np
import pytest

from transit_hunter.batch import (
    KnownCatalog,
    KnownObject,
    Selection,
    Target,
    choose_sectors,
    ctois_from_csv,
    fetch_known_catalog,
    load_or_fetch_catalog,
    match_known,
    parse_sectors,
    read_targets,
    run_batch,
    screen_candidate,
    select_targets,
    summarize_batch,
    write_targets,
)
from transit_hunter.catalog import StellarParams
from transit_hunter.data import NoDataError
from transit_hunter.lightcurve import LightCurve
from transit_hunter.pipeline import PipelineConfig
from transit_hunter.pixels import PixelSource
from transit_hunter.vet import chunk_consistency

PERIOD, T0, DURATION = 3.1, 1401.3, 0.1


def _two_orbit_sectors(dips_in: list[int], n_sectors: int = 2, seed: int = 1) -> LightCurve:
    """Sectors 10, 11, ... of two 12.7-day orbits each, with 1000 ppm dips in ``dips_in``."""
    rng = np.random.default_rng(seed)
    time, sector = [], []
    for k in range(n_sectors):
        for orbit in (0, 1):
            start = 1400 + 27.4 * k + 13.7 * orbit
            t = np.arange(start, start + 12.7, 2 / 1440)
            time.append(t)
            sector.append(np.full(t.size, 10 + k))
    t, s = np.concatenate(time), np.concatenate(sector)
    flux = 1 + 4e-4 * rng.standard_normal(t.size)
    phase = (t - T0 + 0.5 * PERIOD) % PERIOD - 0.5 * PERIOD
    flux[(np.abs(phase) < DURATION / 2) & np.isin(s, dips_in)] -= 1e-3
    return LightCurve(t, flux, np.full(t.size, 4e-4), s)


def test_chunk_consistency_accepts_a_dip_in_every_sector():
    result = chunk_consistency(_two_orbit_sectors([10, 11]), PERIOD, T0, DURATION)
    assert result["chunked_by"] == "sector" and result["n_chunks"] == 2
    assert result["p_value"] > 0.01
    assert result["snr_without_strongest"] > 10


def test_chunk_consistency_flags_a_dip_in_one_sector_only():
    result = chunk_consistency(_two_orbit_sectors([11]), PERIOD, T0, DURATION)
    assert result["strongest"] == "sector 11"
    assert result["snr_without_strongest"] < 3
    assert result["p_value"] < 1e-6
    screen = screen_candidate(_entry(chunks=result))
    assert screen["tier"] == "review"
    assert any("rests on sector 11" in reason for reason in screen["reasons"])


def test_one_sector_is_split_into_its_two_orbits():
    result = chunk_consistency(_two_orbit_sectors([10], n_sectors=1), PERIOD, T0, DURATION)
    assert result["chunked_by"] == "segment" and result["n_chunks"] == 2


def test_sector_lists_parse_and_the_latest_sectors_are_chosen():
    assert parse_sectors("1-3, 7,5") == [1, 2, 3, 5, 7]
    with pytest.raises(ValueError):
        parse_sectors("5-3")
    assert choose_sectors([3, 1, 2, 9], 2) == [3, 9]
    assert choose_sectors([3, 1], None) == [1, 3]
    assert choose_sectors([], 2) is None


def test_targets_round_trip_and_plain_tic_lists_are_read(tmp_path):
    targets = [Target(1, 9.5, 3500.0, 0.4, [1, 2]), Target(22)]
    write_targets(tmp_path / "targets.csv", targets)
    back = read_targets(tmp_path / "targets.csv")
    assert [t.tic_id for t in back] == [1, 22]
    assert back[0].sectors == [1, 2] and back[1].sectors == []
    assert back[0].teff == 3500.0 and math.isnan(back[1].teff)
    (tmp_path / "list.txt").write_text("TIC 5\n# a comment\n7  # another\n")
    assert [t.tic_id for t in read_targets(tmp_path / "list.txt")] == [5, 7]


def test_selection_filters_the_tic_leaves_out_known_hosts_and_is_reproducible():
    lists = {1: {1, 2, 3, 4, 5, 6, 8}, 2: {2, 3, 4, 5, 6, 7, 8}}
    m_dwarf = {"tmag": 11.0, "teff": 3400.0, "radius": 0.4, "lumclass": "DWARF"}
    rows = {
        2: m_dwarf,
        3: m_dwarf,  # hosts a TOI
        4: m_dwarf | {"lumclass": "GIANT"},
        5: m_dwarf | {"teff": 5800.0},
        6: m_dwarf | {"tmag": 14.2},
        8: m_dwarf | {"teff": 3100.0},
    }

    def pick(**kwargs):
        selection = Selection(sectors=[1, 2], min_sectors=2, teff_max=4000.0, **kwargs)
        return select_targets(
            selection,
            known_hosts={3},
            sector_lists=lists.__getitem__,
            tic_rows=lambda ids: {i: rows[i] for i in ids if i in rows},
            report=lambda _: None,
        )

    chosen = pick(seed=3)
    assert sorted(t.tic_id for t in chosen) == [2, 8]  # 1 and 7 are in one sector only
    assert all(t.sectors == [1, 2] for t in chosen)
    assert [t.tic_id for t in pick(seed=3)] == [t.tic_id for t in chosen]
    assert len(pick(seed=3, n=1)) == 1
    assert "no confirmed planet and no TOI" in Selection(sectors=[1, 2]).describe()


CTOI_CSV = (
    "TIC ID,CTOI,Promoted to TOI,User Disposition,TFOPWG Disposition,"
    "Transit Epoch (BJD),Period (days),Depth ppm,Duration (hrs)\n"
    "17361,17361.01,3127.01,PC,,2458596.9598,3.60677,10036,2.1\n"
    "999,999.01,,PC,FP,,,500,\n"
)


def test_the_ctoi_table_is_parsed():
    first, second = ctois_from_csv(CTOI_CSV)
    assert first.tic_id == 17361 and first.name == "CTOI 17361.01 (TOI-3127.01)"
    assert first.period == pytest.approx(3.60677)
    assert first.t0_btjd == pytest.approx(1596.9598)
    assert second.disposition == "FP" and second.period is None and second.t0_btjd is None


def test_period_multiples_match_only_when_the_transits_line_up():
    c = KnownObject("TOI", "TOI-270.02", 259377017, 5.66048, 1461.0, "CP")
    assert match_known(5.662, 1462.5, 0.08, [c])[1] == 1.0  # same period, any phase
    assert match_known(2 * 5.66048, 1461.0 + 3 * 5.66048, 0.08, [c])[1] == 2.0
    assert match_known(5.66048 / 2, 1461.0 + 7 * 5.66048 / 2, 0.08, [c])[1] == 0.5
    # twice the period with transits between c's, as for a planet near 2:1
    assert match_known(2 * 5.66048, 1461.0 + 2.1, 0.08, [c]) is None
    # TOI-270 d's period is 0.5 % from twice c's: not an alias even where they line up
    assert match_known(11.3797, 1461.0, 0.08, [c]) is None


TESTS_PASSED = {
    "odd_even": "pass",
    "secondary": "pass",
    "shape": "pass",
    "density": "pass",
    "radius": "pass",
    "coverage": "pass",
    "rotation": "n/a",
    "centroid": "pass",
}
CONSISTENT = {
    "n_transits": 8,
    "n_chunks": 2,
    "chunked_by": "sector",
    "chunks": [],
    "snr_all": 20.0,
    "snr_without_strongest": 14.0,
    "strongest": "sector 2",
    "p_value": 0.5,
}


def _entry(snr=15.0, sde=12.0, n_transits=8, verdict=None, statuses=None, chunks=CONSISTENT):
    statuses = TESTS_PASSED | (statuses or {})
    return {
        "role": "candidate",
        "signal": {
            "period": 4.2,
            "t0": 1500.0,
            "duration": 0.1,
            "depth": 1e-3,
            "snr": snr,
            "sde": sde,
            "n_transits": n_transits,
        },
        "vetting": {
            "verdict": verdict or "planet candidate (passes all tests)",
            "tests": [
                {"name": n, "status": s, "message": f"{n} says"} for n, s in statuses.items()
            ],
        },
        "chunks": chunks,
    }


def test_screening_sorts_candidates_into_tiers():
    assert screen_candidate(_entry())["tier"] == "prospect"
    near = screen_candidate(_entry(snr=8.5, sde=7.9))  # like the real false alarms
    assert near["tier"] == "review"
    assert near["reasons"][:2] == [
        "S/N 8.5 is below the margin of 10",
        "SDE 7.9 is below the margin of 9",
    ]
    assert screen_candidate(_entry(n_transits=2))["reasons"] == ["only 2 transits"]
    warned = screen_candidate(_entry(statuses={"shape": "warn"}))
    assert warned["reasons"] == ["vetting warnings: shape"]
    no_size = screen_candidate(_entry(statuses={"density": "n/a", "radius": "n/a"}))
    assert no_size["tier"] == "review"  # how TOI-1401.01 got through
    shallow = screen_candidate(_entry(statuses={"centroid": "n/a"}))
    assert shallow["tier"] == "prospect"
    assert shallow["notes"] == ["not tested: centroid (centroid says)"]
    rejected = screen_candidate(
        _entry(verdict="likely false positive", statuses={"radius": "fail"})
    )
    assert rejected["tier"] == "rejected" and rejected["reasons"] == ["failed: radius"]
    known = screen_candidate(_entry(), [KnownObject("CTOI", "CTOI 1.01", 1, 4.2001, 1500.0)])
    assert known["tier"] == "known" and known["match"] == "CTOI 1.01"
    sibling = screen_candidate(_entry(), [KnownObject("TOI", "TOI-9.01", 1, 13.7, 1500.3, "PC")])
    assert sibling["tier"] == "prospect"
    assert sibling["notes"] == ["the star also has TOI-9.01 (PC), P = 13.7000 d"]
    unmatched = screen_candidate(_entry(), missing_catalogs=["CTOI"])
    assert unmatched["reasons"] == ["not cross-matched with: CTOI"]
    one_chunk = screen_candidate(_entry(chunks=CONSISTENT | {"n_chunks": 1}))
    assert one_chunk["tier"] == "review"


def test_catalogue_downloads_that_fail_are_recorded_and_retried(tmp_path):
    def broken():
        raise ConnectionError("no route to host")

    catalog = fetch_known_catalog(
        {"planet": lambda: [KnownObject("planet", "b", 1, 3.0)], "TOI": list, "CTOI": broken},
        report=lambda _: None,
    )
    assert not catalog.complete and catalog.missing() == ["CTOI"]
    assert catalog.hosts() == {1}
    catalog.save(tmp_path / "catalogs.json")
    fresh = KnownCatalog([], {"planet": "ok", "TOI": "ok", "CTOI": "ok"})
    calls = []
    loaded = load_or_fetch_catalog(
        tmp_path / "catalogs.json", fetch=lambda: calls.append(1) or fresh
    )
    assert calls == [1] and loaded.complete  # the incomplete one was downloaded again

    def unexpected():
        raise AssertionError("downloaded a complete, recent catalogue again")

    assert load_or_fetch_catalog(tmp_path / "catalogs.json", fetch=unexpected).complete


def test_a_batch_resumes_records_failures_and_ranks_its_candidates(tmp_path, single_planet_lc):
    lc, planet = single_planet_lc
    targets = [Target(1, sectors=[1, 2]), Target(2), Target(3)]
    fetched = []

    def fetch(tic, cache_dir=None, sectors=None, config=None):
        fetched.append(tic)
        if tic == 1:
            return lc
        if tic == 2:
            raise NoDataError("no SPOC 2-minute light curve")
        raise TimeoutError("MAST did not answer")

    options = {
        "fetch": fetch,
        "stellar_params": lambda tic, header: StellarParams(
            radius=1.0, radius_err=0.03, mass=1.0, mass_err=0.05, teff=5770.0, source="test"
        ),
        "pixel_source": lambda tic, cache: PixelSource.unavailable("no pixels in tests"),
        "report": lambda _: None,
    }
    config = replace(PipelineConfig(), fit_signals=False)
    assert run_batch(targets, tmp_path, config, **options) == {
        "searched": 1,
        "no data": 1,
        "error": 1,
    }
    status = json.loads((tmp_path / "stars" / "TIC_3" / "status.json").read_text())
    assert status["status"] == "error" and "TimeoutError" in status["message"]
    report = json.loads((tmp_path / "stars" / "TIC_1" / "report.json").read_text())
    entry = next(p for p in report["planets"] if p["role"] == "candidate")
    assert entry["chunks"]["n_chunks"] == 2  # recorded for every candidate

    fetched.clear()
    assert run_batch(targets, tmp_path, config, **options) == {}
    assert fetched == []
    assert run_batch(targets, tmp_path, config, retry_failed=True, **options) == {
        "no data": 1,
        "error": 1,
    }
    assert fetched == [2, 3]

    catalog = KnownCatalog(
        [KnownObject("TOI", "TOI-1.01", 1, planet.period, planet.t0, "KP")],
        {"planet": "ok", "TOI": "ok", "CTOI": "ok"},
    )
    summary = summarize_batch(tmp_path, catalog, selection="three test stars")
    assert summary["stars"] == {"searched": 1, "no data": 1, "error": 1}
    assert summary["candidates"]["known"] == 1
    with (tmp_path / "candidates.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["rank"] == "1" and rows[0]["tier"] == "known"
    assert rows[0]["match"] == "TOI-1.01" and rows[0]["folder"] == "stars/TIC_1"
    text = (tmp_path / "candidates.md").read_text()
    assert "Selection: three test stars." in text
    assert "## Known objects found again (1)" in text
    assert "* TIC 3: TimeoutError: MAST did not answer" in text


def test_cut_short_files_mean_search_again_and_never_stop_the_tables(tmp_path):
    from transit_hunter.batch import collect_batch, is_finished, star_folder

    done, cut_status, cut_report, no_status = (Target(t) for t in (1, 2, 3, 4))
    report = {"target": {"sectors": [1]}, "search": {"signals": []}, "planets": []}
    report |= {"search": {"signals": [], "n_detections": 0, "n_candidates": 0}}
    for target, status_text, report_text in (
        (done, '{"status": "searched"}', json.dumps(report)),
        (cut_status, '{"status": "sear', json.dumps(report)),
        (cut_report, '{"status": "searched"}', '{"target": {"sec'),
        (no_status, None, json.dumps(report)),  # stopped before its status was written
    ):
        folder = star_folder(tmp_path, target.tic_id)
        folder.mkdir(parents=True)
        (folder / "report.json").write_text(report_text)
        if status_text is not None:
            (folder / "status.json").write_text(status_text)
    assert [is_finished(tmp_path, t) for t in (done, cut_status, cut_report, no_status)] == [
        True,
        False,
        False,
        False,
    ]
    stars, candidates = collect_batch(tmp_path)
    assert {s["tic_id"]: s["status"] for s in stars} == {1: "searched", 3: "unreadable"}
    assert candidates == []


def test_a_failing_summary_does_not_stop_the_search(tmp_path):
    lines = []

    def broken_summary():
        raise RuntimeError("disk full")

    def fetch(tic, cache_dir=None, sectors=None, config=None):
        raise NoDataError("none")

    counts = run_batch(
        [Target(1), Target(2)],
        tmp_path,
        PipelineConfig(),
        summarize=broken_summary,
        summarize_every=1,
        report=lines.append,
        fetch=fetch,
    )
    assert counts == {"no data": 2}
    assert sum("could not update the tables" in line for line in lines) == 3


def _outage_run(tmp_path, fetch, n=5, **kwargs):
    lines, waits = [], []
    counts = run_batch(
        [Target(i) for i in range(1, n + 1)],
        tmp_path,
        PipelineConfig(),
        report=lines.append,
        pause_after=2,
        pause_seconds=600,
        sleep=waits.append,
        fetch=fetch,
        **kwargs,
    )
    return counts, lines, waits


def test_the_batch_waits_out_an_archive_outage_instead_of_failing_every_star(tmp_path):
    calls = []

    def fetch(tic, cache_dir=None, sectors=None, config=None):
        calls.append(tic)
        if len(calls) <= 4:
            raise ConnectionError("MAST is down")
        raise NoDataError("none")

    counts, lines, waits = _outage_run(tmp_path, fetch, max_pauses=3)
    assert calls == [1, 2, 2, 2, 2, 3, 4, 5]  # star 2 is tried again after each wait
    assert waits == [600, 600, 600]
    assert counts == {"error": 1, "no data": 4}
    assert sum("an archive may be down: waiting 10 min" in line for line in lines) == 3


def test_a_long_outage_stops_the_batch_and_a_bug_never_pauses_it(tmp_path):
    def down(tic, cache_dir=None, sectors=None, config=None):
        raise TimeoutError("no answer")

    counts, lines, waits = _outage_run(tmp_path / "down", down, max_pauses=2)
    assert counts == {"error": 2} and waits == [600, 600]
    assert lines[-1].startswith("stopping: stars have kept failing for 20 min")

    def buggy(tic, cache_dir=None, sectors=None, config=None):
        raise ValueError("a bug, not an outage")

    counts, lines, waits = _outage_run(tmp_path / "buggy", buggy)
    assert counts == {"error": 5} and waits == []
