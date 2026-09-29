#!/usr/bin/env python
"""Measure how well the vetting agrees with the TESS follow-up team on resolved TOIs.

The TESS Follow-up Observing Program Working Group (TFOPWG) gives every TESS
Object of Interest a disposition. Two kinds are settled: confirmed or known
planets (CP, KP) and false positives (FP, mostly eclipsing binaries, often
blended with the target). This script runs the full pipeline on a sample of
each and compares the verdicts with the dispositions.

1. Download the TOI table from the NASA Exoplanet Archive and keep TFOPWG
   dispositions CP and KP ("planet") and FP ("false positive").
2. Apply the same cuts as the candidate vetting (``vet_toi_candidates.py``):
   1 d < P < 15 d, Tmag <= 11, depth >= 800 ppm, one TOI per star, SPOC
   2-minute light curves filed under the TOI's own TIC ID. Within the cuts,
   the order is random with a fixed seed, so that each class is represented as
   it is, not by its most extreme members. The first N of each class are used.
3. Run the pipeline on the first observing season of each star: its first
   sector with 2-minute data and those numbered up to ``--season-sectors - 1``
   after it (about 110 days for the default of 4). Sectors years apart would
   multiply the number of trial periods and the run time. Find the detection at
   the TOI's period (or twice or half of it, as binaries are often catalogued
   at either) and record its verdict and the outcome of every vetting test.
4. Write the agreement table and, per test, how often it fails or warns for
   each class.

A light curve alone cannot tell a planet from an eclipsing binary blended with
the target by a nearby star, which is the most common reason for an FP
disposition; the numbers measure what light-curve vetting can do, not what the
follow-up program does.

Requires network access to exoplanetarchive.ipac.caltech.edu and mast.stsci.edu.

Outputs (in --out): one report folder per TOI, calibration.json, calibration.md.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from dataclasses import replace
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np

from transit_hunter.catalog import TOI, get_stellar_params, query_toi_catalog
from transit_hunter.data import NoDataError, fetch_lightcurve
from transit_hunter.fit import FitConfig
from transit_hunter.pipeline import PipelineConfig, prune_report_figures, run_on_lightcurve
from transit_hunter.pixels import PixelSource
from transit_hunter.search import default_n_workers
from transit_hunter.utils import write_json

CLASSES = {"planet": ("CP", "KP"), "false positive": ("FP",)}
SELECTION = (
    "TFOPWG disposition CP or KP (planet) or FP (false positive); 1 d < P < 15 d; "
    "Tmag <= 11; depth >= 800 ppm; one TOI per star; SPOC 2-minute light curves under "
    "the TOI's own TIC ID; random order within each class (seed {seed}); first {n} of "
    "each class; the first observing season of each star (its first sector with 2-minute "
    "data and those numbered up to {span} after it)"
)
OUTCOMES = (
    "planet candidate (passes all tests)",
    "planet candidate (with caveats)",
    "likely false positive",
    "not recovered by the search",
)
TESTS = ("odd_even", "secondary", "shape", "density", "radius", "coverage", "rotation")
#: The statistic of each test that its thresholds apply to, as (test, key, label). The key
#: is "statistic" or a key of the test's details.
STATISTICS = (
    ("odd_even", "statistic", "odd/even difference (σ)"),
    ("secondary", "statistic", "dip at phase 0.5 (σ)"),
    ("shape", "statistic", "ingress + egress / duration"),
    ("shape", "p_grazing", "posterior P(grazing)"),
    ("density", "ratio", "transit-implied / catalogue density"),
    ("radius", "statistic", "companion radius (R_J)"),
)


def eligible(toi: TOI) -> bool:
    return bool(
        toi.period
        and 1.0 < toi.period < 15.0
        and toi.tmag
        and toi.tmag <= 11.0
        and toi.depth_ppm
        and toi.depth_ppm >= 800
        and toi.t0_btjd is not None
    )


def shuffled(tois: list[TOI], seed: int) -> list[TOI]:
    """Eligible TOIs in a random order that depends only on the seed and the table."""
    ok = sorted((t for t in tois if eligible(t)), key=lambda t: t.toi)
    order = np.random.default_rng(seed).permutation(len(ok))
    return [ok[i] for i in order]


def own_sectors(tic_id: int) -> list[int]:
    """Sectors with SPOC 2-minute light curves filed under this TIC ID.

    A search by name also returns other catalogue entries at the same position,
    whose light curves the pipeline never uses (see ``vet_toi_candidates.py``).
    """
    import lightkurve as lk

    result = lk.search_lightcurve(f"TIC {tic_id}", mission="TESS", author="SPOC", exptime=120)
    if len(result) == 0:
        return []
    return sorted(
        {
            int(sector)
            for sector, name in zip(
                result.table["sequence_number"], result.table["target_name"], strict=True
            )
            if str(name).strip() == str(int(tic_id))
        }
    )


def match_detection(report: dict[str, Any], period: float) -> tuple[dict[str, Any] | None, float]:
    """The candidate at the catalogue period, or else at twice or half of it."""
    candidates = [p for p in report["planets"] if p.get("role") == "candidate"]
    for ratio in (1.0, 2.0, 0.5):
        for p in candidates:
            if abs(p["signal"]["period"] / (ratio * period) - 1.0) < 0.01:
                return p, ratio
    return None, float("nan")


def select(n: int, seed: int, season_sectors: int) -> list[tuple[str, TOI, list[int]]]:
    """The first ``n`` eligible TOIs of each class with 2-minute data, one per star."""
    chosen: list[tuple[str, TOI, list[int]]] = []
    seen_tics: set[int] = set()
    for label, dispositions in CLASSES.items():
        pool = [t for d in dispositions for t in query_toi_catalog(d)]
        taken = 0
        for toi in shuffled(pool, seed):
            if toi.tic_id in seen_tics:
                continue  # one TOI per star keeps the sample diverse
            sectors = own_sectors(toi.tic_id)
            if not sectors:
                continue
            season = [s for s in sectors if s < sectors[0] + season_sectors]
            chosen.append((label, toi, season))
            seen_tics.add(toi.tic_id)
            taken += 1
            if taken == n:
                break
    return chosen


def summarize(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Agreement table and per-test outcome counts for each class."""
    table = {c: Counter(e["verdict"] for e in entries if e["class"] == c) for c in CLASSES}
    tests: dict[str, dict[str, Counter]] = {}
    for name in TESTS:
        tests[name] = {}
        for c in CLASSES:
            tests[name][c] = Counter(
                e["tests"][name]["status"]
                for e in entries
                if e["class"] == c and e["tests"] and name in e["tests"]
            )
    statistics = {}
    for name, key, label in STATISTICS:
        statistics[label] = {}
        for c in CLASSES:
            values = [
                e["tests"][name][key]
                for e in entries
                if e["class"] == c and e["tests"] and e["tests"].get(name, {}).get(key) is not None
            ]
            values = [v for v in values if v == v]  # NaN for a test that could not run
            statistics[label][c] = (
                {"n": len(values), "min": min(values), "median": median(values), "max": max(values)}
                if values
                else {"n": 0}
            )
    return {
        "agreement": {c: dict(table[c]) for c in CLASSES},
        "tests": {n: {c: dict(v) for c, v in d.items()} for n, d in tests.items()},
        "statistics": statistics,
    }


def markdown(entries: list[dict[str, Any]], summary: dict[str, Any], selection: str) -> str:
    n = {c: sum(e["class"] == c for e in entries) for c in CLASSES}
    lines = [
        f"Selection: {selection}.",
        "",
        "| TFOPWG class | TOIs | " + " | ".join(OUTCOMES) + " |",
        "|---|---|" + "---|" * len(OUTCOMES),
    ]
    for c in CLASSES:
        row = summary["agreement"][c]
        lines.append(f"| {c} | {n[c]} | " + " | ".join(str(row.get(o, 0)) for o in OUTCOMES) + " |")
    lines += [
        "",
        "Outcome of each vetting test for the recovered TOIs (fail / warn / pass / n/a):",
        "",
        "| test | " + " | ".join(CLASSES) + " |",
        "|---|" + "---|" * len(CLASSES),
    ]
    for name in TESTS:
        cells = []
        for c in CLASSES:
            k = summary["tests"][name][c]
            cells.append(
                f"{k.get('fail', 0)} / {k.get('warn', 0)} / {k.get('pass', 0)} / {k.get('n/a', 0)}"
            )
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "The statistic each test's thresholds apply to, for the recovered TOIs: median and "
        "range (number of TOIs).",
        "",
        "| statistic | " + " | ".join(CLASSES) + " |",
        "|---|" + "---|" * len(CLASSES),
    ]
    for label, by_class in summary["statistics"].items():
        cells = []
        for c in CLASSES:
            v = by_class[c]
            cells.append(
                "–"
                if not v["n"]
                else f"{v['median']:.2f} ({v['min']:.2f} to {v['max']:.2f}; {v['n']})"
            )
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "| TOI | TIC | TFOPWG | P (d) | depth (ppm) | sectors | found at | verdict "
        "| tests failed |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for e in entries:
        failed = ", ".join(k for k, v in (e["tests"] or {}).items() if v["status"] == "fail")
        found = "–" if not e["recovered"] else f"{e['period_ratio']:g} × P"
        lines.append(
            f"| {e['toi']} | {e['tic_id']} | {e['disposition']} | {e['catalog']['period']:.4f} | "
            f"{e['catalog']['depth_ppm']:.0f} | {len(e['sectors'])} | {found} | {e['verdict']} | "
            f"{failed or '–'} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--n", type=int, default=15, help="TOIs per class")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--season-sectors",
        type=int,
        default=4,
        help="use the first sector and those numbered up to this many minus one after it",
    )
    parser.add_argument("--out", type=Path, default=Path("results/toi_calibration"))
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="reuse report folders that already contain report.json (resume a stopped run)",
    )
    parser.add_argument("--dry-run", action="store_true", help="only list the selected TOIs")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)

    workers = args.workers or default_n_workers()
    config = PipelineConfig()
    config = replace(
        config,
        search=replace(config.search, n_workers=workers),
        fit=FitConfig(n_workers=workers),
    )
    selection = SELECTION.format(seed=args.seed, n=args.n, span=args.season_sectors - 1)

    previous = args.out / "calibration.json"
    if args.reuse and previous.exists():  # the same sample, without querying the archives
        chosen = [
            (e["class"], TOI(**e["catalog"]), e["sectors"])
            for e in json.loads(previous.read_text())["tois"]
        ]
    else:
        chosen = select(args.n, args.seed, args.season_sectors)

    if args.dry_run:
        for label, toi, sectors in chosen:
            print(
                f"{label:15s} {toi.name:12s} {toi.disposition} TIC {toi.tic_id} P={toi.period:.4f} "
                f"depth={toi.depth_ppm:.0f} Tmag={toi.tmag:.2f} sectors={sectors}"
            )
        return

    entries = []
    for label, toi, sectors in chosen:
        folder = args.out / toi.name.replace(".", "_")
        if args.reuse and (folder / "report.json").exists():
            report = json.loads((folder / "report.json").read_text())
        else:
            try:
                lc = fetch_lightcurve(
                    toi.tic_id, cache_dir=args.cache_dir, sectors=sectors, config=config.cleaning
                )
            except NoDataError as exc:
                print(f"{toi.name}: {exc}")
                continue
            stellar = get_stellar_params(toi.tic_id, lc.meta.get("stellar_header"))
            pixels = PixelSource(toi.tic_id, cache_dir=args.cache_dir)
            report = run_on_lightcurve(lc, folder, stellar, config, name=toi.name, pixels=pixels)
        match, ratio = match_detection(report, toi.period)
        candidates = [p for p in report["planets"] if p.get("role") == "candidate"]
        keep = {f"vetting_{candidates.index(match) + 1}.png"} if match else {"periodogram_1.png"}
        # The figure the verdict rests on, or the first periodogram if nothing was found.
        report = prune_report_figures(folder, report, keep)
        tests = (
            {
                t["name"]: {"status": t["status"], "statistic": t["statistic"]}
                | {k: t["details"][k] for k in ("ratio", "p_grazing") if k in t["details"]}
                for t in match["vetting"]["tests"]
            }
            if match
            else None
        )
        entry = {
            "toi": toi.name,
            "tic_id": toi.tic_id,
            "class": label,
            "disposition": toi.disposition,
            "catalog": toi.__dict__,
            "sectors": report["target"]["sectors"],
            "report_folder": str(folder),
            "recovered": match is not None,
            "period_ratio": ratio,
            "verdict": match["vetting"]["verdict"] if match else "not recovered by the search",
            "reasons": match["vetting"]["reasons"] if match else [],
            "tests": tests,
            "dropped_transits": len(match.get("dropped_transits", [])) if match else 0,
        }
        entries.append(entry)
        print(f"{toi.name} ({toi.disposition}, TIC {toi.tic_id}): {entry['verdict']}", flush=True)

    summary = summarize(entries)
    write_json(
        args.out / "calibration.json",
        {"selection": selection, "summary": summary, "tois": entries},
    )
    (args.out / "calibration.md").write_text(markdown(entries, summary, selection))
    print(markdown(entries, summary, selection))


if __name__ == "__main__":
    main()
