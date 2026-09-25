#!/usr/bin/env python
"""Measure how the BLS search cost scales with the amount of data.

Simulates noise-only TESS-like light curves of increasing length (contiguous sectors,
plus one multi-year case with a gap) and records, for one search iteration: number of
points, trial periods, effective independent trials, the trial-corrected S/N threshold,
and wall-clock time. Results depend on the machine; the core count is recorded.

Outputs (in --out): search_scaling.json, search_scaling.md
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import time
from pathlib import Path

import numpy as np

from transit_hunter.detrend import detrend
from transit_hunter.lightcurve import LightCurve
from transit_hunter.search import (
    SearchConfig,
    effective_trials,
    find_signal,
    make_period_grid,
    trial_corrected_threshold,
)
from transit_hunter.synthetic import NoiseModel, SyntheticStar, simulate_lightcurve
from transit_hunter.utils import write_json

NOISE = NoiseModel(white_ppm=300, red_ppm=40, rotation_ppm=800, rotation_period=12.0)


def light_curve(case: str, seed: int) -> LightCurve:
    star = SyntheticStar()
    if case == "26 sectors over 3 years":
        a = simulate_lightcurve(star, NOISE, n_sectors=13, seed=seed, start=2000.0)
        b = simulate_lightcurve(star, NOISE, n_sectors=13, seed=seed + 1, start=2730.0)
        return LightCurve(
            np.r_[a.time, b.time],
            np.r_[a.flux, b.flux],
            np.r_[a.flux_err, b.flux_err],
            np.r_[a.sector, b.sector + 26],
        )
    n = int(case.split()[0])
    return simulate_lightcurve(star, NOISE, n_sectors=n, seed=seed)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=Path("results/performance"))
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    parser.add_argument(
        "--markdown-only",
        action="store_true",
        help="only rebuild search_scaling.md from an existing search_scaling.json",
    )
    args = parser.parse_args()
    if args.markdown_only:
        saved = json.loads((args.out / "search_scaling.json").read_text())
        write_markdown(saved["rows"], saved["machine"], args.out)
        return
    cases = ["1 sector", "3 sectors", "13 sectors", "26 sectors over 3 years"]
    rows = []
    for i, case in enumerate(cases):
        lc = light_curve(case, seed=500 + 10 * i)
        flat = detrend(lc).flat
        for density in (1.0, None):
            if density is None and case != "26 sectors over 3 years":
                continue  # the unknown-density case is only timed at the largest size
            cfg = SearchConfig(n_workers=args.workers, stellar_density=density)
            grid = make_period_grid(flat.baseline, cfg)
            n_trials = effective_trials(grid)
            start = time.perf_counter()
            signal, _ = find_signal(flat, cfg)
            elapsed = time.perf_counter() - start
            rows.append(
                {
                    "case": case,
                    "stellar_density_known": density is not None,
                    "n_points": len(flat),
                    "baseline_days": flat.baseline,
                    "n_trial_periods": grid.size,
                    "n_effective_trials": n_trials,
                    "trial_corrected_snr_1pct": trial_corrected_threshold(n_trials, 0.01),
                    "snr_threshold_applied": max(
                        cfg.snr_threshold, trial_corrected_threshold(n_trials, 0.01)
                    ),
                    "seconds_per_iteration": elapsed,
                    "top_peak_period": None if signal is None else signal.period,
                    "top_peak_snr": None if signal is None else signal.snr,
                    "top_peak_sde": None if signal is None else signal.sde,
                    "top_peak_detected": signal is not None and signal.detected,
                    "skipped_peaks": [] if signal is None else signal.skipped_peaks,
                }
            )
            print(rows[-1], flush=True)
    meta = {
        "workers": args.workers,
        "cpu_count": os.cpu_count(),
        "machine": platform.machine(),
        "python": platform.python_version(),
    }
    write_json(args.out / "search_scaling.json", {"machine": meta, "rows": rows})
    write_markdown(rows, meta, args.out)


def write_markdown(rows: list[dict], meta: dict, out: Path) -> None:
    """Write search_scaling.md from the rows of search_scaling.json."""
    lines = [
        f"One BLS iteration on noise-only synthetic light curves, {meta['workers']} worker "
        f"processes ({meta['machine']}, {meta['cpu_count']} CPUs).",
        "",
        "| data | ρ* known | points | trial periods | effective trials | S/N threshold "
        "(trial-corrected 1 %) | time per iteration (s) | top noise peak S/N / SDE |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['case']} ({r['baseline_days']:.0f} d) | "
            f"{'yes' if r['stellar_density_known'] else 'no'} | {r['n_points']} | "
            f"{r['n_trial_periods']} | {r['n_effective_trials']:.2g} | "
            f"{r['snr_threshold_applied']:.2f} ({r['trial_corrected_snr_1pct']:.2f}) | "
            f"{r['seconds_per_iteration']:.{1 if r['seconds_per_iteration'] < 10 else 0}f} | "
            f"{r['top_peak_snr']:.1f} / {r['top_peak_sde']:.1f} |"
        )
    skipped = [
        (r, peak)
        for r in rows
        for peak in r["skipped_peaks"]
        if "stellar variability" in peak["reason"]
    ]
    if skipped:
        lines += ["", "Peaks skipped as stellar variability before the top peak was chosen:", ""]
        for r, peak in skipped:
            known = "known" if r["stellar_density_known"] else "unknown"
            lines.append(
                f"* {r['case']} (ρ* {known}): P = {peak['period']:.2f} d, "
                f"SDE {peak['sde']:.1f}: {peak['reason']}"
            )
    (out / "search_scaling.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
