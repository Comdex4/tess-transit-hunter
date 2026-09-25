#!/usr/bin/env python
"""Vet TESS Objects of Interest that are still planet candidates ("PC").

1. Download the TOI table from the NASA Exoplanet Archive and keep TFOPWG
   disposition "PC".
2. Select candidates with a deterministic, documented rule: 1 d < P < 15 d,
   Tmag <= 11, depth >= 800 ppm, ranked by the S/N proxy
   ``depth * 10**(-0.2 * (Tmag - 10)) * sqrt(27.4 / P)`` (brighter, deeper and
   more frequent transits first); keep the first N that have SPOC 2-minute data.
3. Run the full pipeline on each and match the detection to the TOI ephemeris.
4. Write a per-candidate verdict with the reasoning from every vetting test.

Requires network access to exoplanetarchive.ipac.caltech.edu and mast.stsci.edu.

Outputs (in --out): one report folder per TOI, candidates.json, candidates.md.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from dataclasses import replace
from pathlib import Path

from transit_hunter.catalog import TOI, get_stellar_params, query_toi_catalog
from transit_hunter.data import NoDataError, fetch_lightcurve
from transit_hunter.fit import FitConfig
from transit_hunter.pipeline import PipelineConfig, run_on_lightcurve
from transit_hunter.search import default_n_workers
from transit_hunter.utils import write_json

SELECTION = (
    "TFOPWG disposition PC; 1 d < P < 15 d; Tmag <= 11; depth >= 800 ppm; ranked by "
    "depth * 10**(-0.2 * (Tmag - 10)) * sqrt(27.4 / P); one TOI per star; first N with "
    "SPOC 2-minute light curves"
)


def snr_proxy(toi: TOI) -> float:
    return toi.depth_ppm * 10 ** (-0.2 * (toi.tmag - 10.0)) * math.sqrt(27.4 / toi.period)


def select(tois: list[TOI]) -> list[TOI]:
    ok = [
        t
        for t in tois
        if t.period
        and 1.0 < t.period < 15.0
        and t.tmag
        and t.tmag <= 11.0
        and t.depth_ppm
        and t.depth_ppm >= 800
        and t.t0_btjd is not None
    ]
    return sorted(ok, key=snr_proxy, reverse=True)


def has_2min_data(tic_id: int) -> bool:
    import lightkurve as lk

    return (
        len(lk.search_lightcurve(f"TIC {tic_id}", mission="TESS", author="SPOC", exptime=120)) > 0
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--n", type=int, default=5, help="number of candidates (3-5)")
    parser.add_argument("--out", type=Path, default=Path("results/candidates"))
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="reuse report folders that already contain report.json (resume a stopped run)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)

    workers = args.workers or default_n_workers()
    fit = FitConfig(n_workers=workers)
    if args.quick:
        fit = replace(fit, n_walkers=32, max_steps=3000, min_steps=1000)
    config = PipelineConfig()
    config = replace(config, search=replace(config.search, n_workers=workers), fit=fit)

    pcs = query_toi_catalog("PC")
    chosen: list[TOI] = []
    seen_tics: set[int] = set()
    for toi in select(pcs):
        if toi.tic_id in seen_tics:
            continue  # one candidate per star keeps the sample diverse
        if has_2min_data(toi.tic_id):
            chosen.append(toi)
            seen_tics.add(toi.tic_id)
        if len(chosen) == args.n:
            break

    entries = []
    for toi in chosen:
        folder = args.out / toi.name.replace(".", "_")
        if args.reuse and (folder / "report.json").exists():
            report = json.loads((folder / "report.json").read_text())
            print(f"{toi.name}: reusing {folder / 'report.json'}")
        else:
            try:
                lc = fetch_lightcurve(toi.tic_id, cache_dir=args.cache_dir, config=config.cleaning)
            except NoDataError as exc:
                print(f"{toi.name}: {exc}")
                continue
            stellar = get_stellar_params(toi.tic_id, lc.meta.get("stellar_header"))
            report = run_on_lightcurve(lc, folder, stellar, config, name=toi.name)
        candidates = [p for p in report["planets"] if p.get("role") == "candidate"]
        match = next(
            (p for p in candidates if abs(p["signal"]["period"] - toi.period) < 0.01 * toi.period),
            None,
        )
        entry = {
            "toi": toi.name,
            "tic_id": toi.tic_id,
            "catalog": toi.__dict__,
            "snr_proxy": snr_proxy(toi),
            "sectors": report["target"]["sectors"],
            "report_folder": str(folder),
            "recovered": match is not None,
            "verdict": match["vetting"]["verdict"] if match else "not recovered by the search",
            "reasons": match["vetting"]["reasons"] if match else [],
            "fit": match.get("fit") if match else None,
            "signal": match["signal"] if match else None,
        }
        entries.append(entry)
        print(f"{toi.name} (TIC {toi.tic_id}): {entry['verdict']}")

    write_json(args.out / "candidates.json", {"selection": SELECTION, "candidates": entries})
    lines = [
        "| TOI | TIC | catalogue P (d) | recovered P (d) | Rp (R⊕) | verdict |",
        "|---|---|---|---|---|---|",
    ]
    for e in entries:
        rp = ((e["fit"] or {}).get("posterior", {}).get("rp_earth") or {}).get("median")
        period = f"{e['signal']['period']:.5f}" if e["signal"] else "–"
        radius = f"{rp:.2f}" if rp is not None else "–"
        lines.append(
            f"| {e['toi']} | {e['tic_id']} | {e['catalog']['period']:.5f} | {period} | "
            f"{radius} | {e['verdict']} |"
        )
    for e in entries:
        lines += ["", f"### {e['toi']}", ""] + [f"* {r}" for r in e["reasons"]]
    (args.out / "candidates.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
