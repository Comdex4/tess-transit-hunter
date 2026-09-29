#!/usr/bin/env python
"""Measure the pipeline's false-alarm rate on real stars with no known planets or TOIs.

The noise-only calibration (``calibrate_false_alarms.py``) uses simulated light
curves, which have none of the instrumental systematics of real TESS data
(momentum dumps, scattered light, thermal settling after data downlinks), so
its false-alarm rates are lower limits. Here the full pipeline runs on real
light curves of stars around which neither TESS nor anyone else has found a
transiting planet:

1. List the stars with SPOC 2-minute light curves in both of two sectors
   (default 1 and 2) from MAST.
2. Remove every TOI host, whatever the TOI's disposition, and every host of a
   confirmed planet (NASA Exoplanet Archive), and keep dwarfs (TIC luminosity
   class) with Tmag <= 11, like the TOI candidates the pipeline vets.
3. Take N of them at random with a fixed seed.
4. Run the full pipeline (search, fit, vetting) on the two sectors of each.

Any detection on these stars is a false alarm of the planet search, except that
the light curve may hold a real signal that is not a planet (an eclipsing
binary among them, which is left to the vetting) or, rarely, a planet nobody
has found. The vetting verdicts show how many false alarms would survive as
planet candidates.

Requires network access to mast.stsci.edu and exoplanetarchive.ipac.caltech.edu.

Outputs (in --out): stars.csv, summary.json, false_alarms_real.md, and one
report folder per star (with the vetting figure of each detection).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from transit_hunter.catalog import get_stellar_params, parse_tic_id
from transit_hunter.data import NoDataError, fetch_lightcurve
from transit_hunter.fit import FitConfig
from transit_hunter.pipeline import PipelineConfig, prune_report_figures, run_on_lightcurve
from transit_hunter.pixels import PixelSource
from transit_hunter.search import default_n_workers
from transit_hunter.utils import write_json

SELECTION = (
    "stars with SPOC 2-minute light curves in sectors {s1} and {s2}; no TOI of any "
    "disposition and no confirmed planet (NASA Exoplanet Archive); TIC luminosity class "
    "DWARF; Tmag <= {tmag:g}; {n} drawn at random (seed {seed}) from the stars sorted by TIC ID"
)
FIELDS = [
    "tic_id",
    "tmag",
    "teff",
    "radius",
    "n_points",
    "cdpp_1h_ppm",
    "top_period",
    "top_sde",
    "top_snr",
    "n_detections",
    "n_candidates",
    "detections",
]


def sector_targets(sector: int) -> set[int]:
    """TIC IDs with a SPOC 2-minute light curve in ``sector``."""
    from astroquery.mast import Observations

    obs = Observations.query_criteria(
        obs_collection="TESS",
        dataproduct_type="timeseries",
        sequence_number=sector,
        provenance_name="SPOC",
    )
    return {int(t) for t, e in zip(obs["target_name"], obs["t_exptime"], strict=True) if e == 120}


def planet_and_toi_hosts() -> set[int]:
    """TIC IDs of every TOI host and every confirmed-planet host."""
    from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive

    tois = NasaExoplanetArchive.query_criteria(table="toi", select="tid")
    hosts = {int(t) for t in tois["tid"]}
    planets = NasaExoplanetArchive.query_criteria(table="pscomppars", select="tic_id")
    hosts |= {parse_tic_id(t) for t in planets["tic_id"] if parse_tic_id(t)}
    return hosts


def tic_rows(tic_ids: list[int]) -> dict[int, dict[str, Any]]:
    """Tmag, Teff, radius and luminosity class from the TIC."""
    from astroquery.mast import Catalogs

    table = Catalogs.query_criteria(catalog="Tic", ID=[int(t) for t in tic_ids])
    out = {}
    for row in table:
        out[int(row["ID"])] = {
            "tmag": float(row["Tmag"]),
            "teff": float(row["Teff"]) if row["Teff"] is not np.ma.masked else math.nan,
            "radius": float(row["rad"]) if row["rad"] is not np.ma.masked else math.nan,
            "lumclass": str(row["lumclass"]),
        }
    return out


def select_stars(
    sectors: tuple[int, int], n: int, seed: int, max_tmag: float
) -> list[tuple[int, dict[str, Any]]]:
    both = sorted(sector_targets(sectors[0]) & sector_targets(sectors[1]))
    hosts = planet_and_toi_hosts()
    pool = [t for t in both if t not in hosts]
    order = np.random.default_rng(seed).permutation(len(pool))
    chosen: list[tuple[int, dict[str, Any]]] = []
    for start in range(0, len(order), 200):
        batch = [pool[i] for i in order[start : start + 200]]
        info = tic_rows(batch)
        for tic in batch:  # keep the random order
            row = info.get(tic)
            if row and row["lumclass"] == "DWARF" and row["tmag"] <= max_tmag:
                chosen.append((tic, row))
                if len(chosen) == n:
                    return chosen
    return chosen


def star_row(tic: int, info: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    signals = report["search"]["signals"]
    top = signals[0] if signals else None
    return {
        "tic_id": tic,
        "tmag": info["tmag"],
        "teff": info["teff"],
        "radius": info["radius"],
        "n_points": report["target"]["n_points"],
        "cdpp_1h_ppm": report["noise"]["robust_cdpp_ppm"]["1h"],
        "top_period": top["period"] if top else math.nan,
        "top_sde": top["sde"] if top else math.nan,
        "top_snr": top["snr"] if top else math.nan,
        "n_detections": report["search"]["n_detections"],
        "n_candidates": report["search"]["n_candidates"],
        "detections": "; ".join(
            f"P={p['signal']['period']:.4f} d, depth {p['signal']['depth'] * 1e6:.0f} ppm, "
            f"S/N {p['signal']['snr']:.1f}, SDE {p['signal']['sde']:.1f}: "
            f"{p['vetting']['verdict']}"
            for p in report["planets"]
        ),
    }


def summarize(rows: list[dict[str, Any]], planets: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    with_detection = sum(r["n_detections"] > 0 for r in rows)
    verdicts: dict[str, int] = {}
    for p in planets:
        verdicts[p["verdict"]] = verdicts.get(p["verdict"], 0) + 1
    passed = [p for p in planets if p["verdict"].startswith("planet candidate")]
    sde = np.array([r["top_sde"] for r in rows], dtype=float)
    snr = np.array([r["top_snr"] for r in rows], dtype=float)
    return {
        "n_stars": n,
        "n_with_detection": with_detection,
        "n_detections": len(planets),
        "n_stars_with_surviving_candidate": len({p["tic_id"] for p in passed}),
        "verdicts": verdicts,
        "top_peak_sde": {
            "median": float(np.nanmedian(sde)),
            "p99": float(np.nanpercentile(sde, 99)),
            "max": float(np.nanmax(sde)),
        },
        "top_peak_snr": {
            "median": float(np.nanmedian(snr)),
            "p99": float(np.nanpercentile(snr, 99)),
            "max": float(np.nanmax(snr)),
        },
        "median_cdpp_1h_ppm": float(np.median([r["cdpp_1h_ppm"] for r in rows])),
    }


def markdown(summary: dict[str, Any], planets: list[dict[str, Any]], selection: str) -> str:
    s = summary
    lines = [
        f"Selection: {selection}.",
        "",
        f"* Stars searched: {s['n_stars']} (median 1-h scatter {s['median_cdpp_1h_ppm']:.0f} ppm)",
        f"* Stars with at least one detection: {s['n_with_detection']} "
        f"({100 * s['n_with_detection'] / max(s['n_stars'], 1):.1f} %)",
        f"* Detections: {s['n_detections']}; stars with a detection the vetting leaves as a "
        f"planet candidate: {s['n_stars_with_surviving_candidate']}",
        f"* Strongest peak of the first search pass: SDE median {s['top_peak_sde']['median']:.1f}, "
        f"99th percentile {s['top_peak_sde']['p99']:.1f}, maximum {s['top_peak_sde']['max']:.1f}; "
        f"S/N median {s['top_peak_snr']['median']:.1f}, 99th percentile "
        f"{s['top_peak_snr']['p99']:.1f}, maximum {s['top_peak_snr']['max']:.1f}",
        "",
    ]
    if planets:
        lines += [
            "| TIC | P (d) | depth (ppm) | S/N | SDE | transits | verdict | failed tests |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for p in planets:
            lines.append(
                f"| {p['tic_id']} | {p['period']:.4f} | {p['depth_ppm']:.0f} | {p['snr']:.1f} | "
                f"{p['sde']:.1f} | {p['n_transits']} | {p['verdict']} | "
                f"{', '.join(p['failed']) or '–'} |"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--n", type=int, default=100, help="number of stars")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--sectors", type=int, nargs=2, default=(1, 2))
    parser.add_argument("--max-tmag", type=float, default=11.0)
    parser.add_argument("--out", type=Path, default=Path("results/false_alarms_real"))
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="reuse report folders that already contain report.json (resume a stopped run)",
    )
    parser.add_argument("--dry-run", action="store_true", help="only list the selected stars")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)

    workers = args.workers or default_n_workers()
    config = PipelineConfig()
    config = replace(
        config,
        search=replace(config.search, n_workers=workers),
        fit=FitConfig(n_workers=workers),
    )
    s1, s2 = args.sectors
    selection = SELECTION.format(s1=s1, s2=s2, tmag=args.max_tmag, n=args.n, seed=args.seed)
    previous = args.out / "stars.csv"
    if args.reuse and previous.exists():  # the same sample, without querying the archives
        with previous.open(newline="") as handle:
            stars = [
                (
                    int(row["tic_id"]),
                    {k: float(row[k]) for k in ("tmag", "teff", "radius")},
                )
                for row in csv.DictReader(handle)
            ]
    else:
        stars = select_stars((s1, s2), args.n, args.seed, args.max_tmag)
    if args.dry_run:
        for tic, info in stars:
            print(f"TIC {tic}: Tmag {info['tmag']:.2f}, Teff {info['teff']:.0f} K")
        print(f"{len(stars)} stars")
        return

    rows, planets = [], []
    for tic, info in stars:
        folder = args.out / "stars" / f"TIC_{tic}"
        if args.reuse and (folder / "report.json").exists():
            report = json.loads((folder / "report.json").read_text())
        else:
            try:
                lc = fetch_lightcurve(
                    tic, cache_dir=args.cache_dir, sectors=[s1, s2], config=config.cleaning
                )
            except NoDataError as exc:
                print(f"TIC {tic}: {exc}")
                continue
            stellar = get_stellar_params(tic, lc.meta.get("stellar_header"))
            pixels = PixelSource(tic, cache_dir=args.cache_dir)
            report = run_on_lightcurve(
                lc, folder, stellar, config, name=f"TIC {tic}", pixels=pixels
            )
        # Keep only the vetting figure of each detection (none without one).
        keep = {v for k, v in report["figures"].items() if k.startswith("vetting_")}
        report = prune_report_figures(folder, report, keep)
        row = star_row(tic, info, report)
        rows.append(row)
        for p in report["planets"]:
            tests = p["vetting"].get("tests", [])
            planets.append(
                {
                    "tic_id": tic,
                    "role": p["role"],
                    "period": p["signal"]["period"],
                    "depth_ppm": p["signal"]["depth"] * 1e6,
                    "snr": p["signal"]["snr"],
                    "sde": p["signal"]["sde"],
                    "n_transits": p["signal"]["n_transits"],
                    "verdict": p["vetting"]["verdict"],
                    "failed": [t["name"] for t in tests if t["status"] == "fail"],
                }
            )
        print(f"TIC {tic}: {row['n_detections']} detection(s) {row['detections']}", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "stars.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary = summarize(rows, planets)
    write_json(
        args.out / "summary.json",
        {"selection": selection, "summary": summary, "detections": planets},
    )
    text = markdown(summary, planets, selection)
    (args.out / "false_alarms_real.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
