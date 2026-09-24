#!/usr/bin/env python
"""Calibrate the BLS detection thresholds on noise-only synthetic light curves.

For each noise regime, simulate light curves *without* transits, detrend them,
run one BLS pass, and record the SDE and S/N of the strongest peak. The fraction
of noise-only light curves whose top peak passes the detection thresholds is
the false-alarm probability per star (for this noise model).

Outputs (in --out): false_alarms.csv, summary.json, false_alarms.md, false_alarms.png

Caveat: real TESS light curves contain systematics (momentum dumps, scattered
light, residual pointing jitter) that this noise model does not reproduce, so
real-data false-alarm rates will be higher. See docs/limitations.md.
"""

from __future__ import annotations

import argparse
import csv
import logging
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from transit_hunter.detrend import DetrendConfig, detrend
from transit_hunter.plotting import AQUA, BLUE, INK_MUTED, ORANGE, new_figure, save_figure, style
from transit_hunter.search import SearchConfig, find_signal
from transit_hunter.synthetic import NoiseModel, SyntheticStar, simulate_lightcurve
from transit_hunter.utils import binned_rms, write_json

REGIMES = {
    "quiet": NoiseModel(
        white_ppm=300, red_ppm=30, red_timescale=0.05, rotation_ppm=500, rotation_period=12.0
    ),
    "moderate": NoiseModel(
        white_ppm=800, red_ppm=80, red_timescale=0.05, rotation_ppm=2000, rotation_period=7.0
    ),
    "active": NoiseModel(
        white_ppm=800, red_ppm=150, red_timescale=0.1, rotation_ppm=8000, rotation_period=3.0
    ),
}
CASES = [("quiet", 1), ("moderate", 1), ("active", 1), ("moderate", 3)]


def run_case(task: tuple[str, int, int]) -> dict:
    regime, n_sectors, seed = task
    lc = simulate_lightcurve(SyntheticStar(), REGIMES[regime], (), n_sectors=n_sectors, seed=seed)
    flat = detrend(lc, DetrendConfig()).flat
    signal, _ = find_signal(flat, SearchConfig(n_workers=1))
    row = {
        "regime": regime,
        "n_sectors": n_sectors,
        "seed": seed,
        "cdpp_1h_ppm": binned_rms(flat.time, flat.flux, 1 / 24) * 1e6,
    }
    if signal is None:
        row.update(period=np.nan, sde=np.nan, snr=np.nan, depth_ppm=np.nan, n_transits=0)
    else:
        row.update(
            period=signal.period,
            sde=signal.sde,
            snr=signal.snr,
            depth_ppm=signal.depth * 1e6,
            n_transits=signal.n_transits,
        )
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--n", type=int, default=150, help="light curves per case")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", type=Path, default=Path("results/calibration"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    args.out.mkdir(parents=True, exist_ok=True)

    tasks = [
        (regime, sectors, 10_000 * k + i)
        for k, (regime, sectors) in enumerate(CASES)
        for i in range(args.n)
    ]
    start = time.time()
    with ProcessPoolExecutor(args.workers) as pool:
        rows = list(pool.map(run_case, tasks, chunksize=4))
    elapsed = time.time() - start

    with (args.out / "false_alarms.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    cfg = SearchConfig()
    summary = {
        "n_per_case": args.n,
        "runtime_s": elapsed,
        "sde_threshold": cfg.sde_threshold,
        "snr_threshold": cfg.snr_threshold,
        "cases": [],
    }
    for regime, sectors in CASES:
        sel = [r for r in rows if r["regime"] == regime and r["n_sectors"] == sectors]
        sde = np.array([r["sde"] for r in sel], dtype=float)
        snr = np.array([r["snr"] for r in sel], dtype=float)
        passed = (sde >= cfg.sde_threshold) & (snr >= cfg.snr_threshold)
        summary["cases"].append(
            {
                "regime": regime,
                "n_sectors": sectors,
                "noise_model": REGIMES[regime].__dict__,
                "median_cdpp_1h_ppm": float(np.median([r["cdpp_1h_ppm"] for r in sel])),
                "sde_percentiles": dict(
                    zip(
                        ("50", "90", "99", "max"),
                        map(float, np.nanpercentile(sde, [50, 90, 99, 100])),
                        strict=True,
                    )
                ),
                "snr_percentiles": dict(
                    zip(
                        ("50", "90", "99", "max"),
                        map(float, np.nanpercentile(snr, [50, 90, 99, 100])),
                        strict=True,
                    )
                ),
                "n_false_alarms": int(passed.sum()),
                "false_alarm_fraction": float(passed.mean()),
            }
        )
    write_json(args.out / "summary.json", summary)

    lines = [
        f"Noise-only synthetic light curves, {args.n} per case; thresholds SDE ≥ "
        f"{cfg.sde_threshold:g} and S/N ≥ {cfg.snr_threshold:g}.",
        "",
        "| noise regime | sectors | median 1-h CDPP (ppm) | SDE median / 99th pct / max | "
        "S/N median / 99th pct / max | false alarms |",
        "|---|---|---|---|---|---|",
    ]
    for case in summary["cases"]:
        s, n = case["sde_percentiles"], case["snr_percentiles"]
        lines.append(
            f"| {case['regime']} | {case['n_sectors']} | {case['median_cdpp_1h_ppm']:.0f} | "
            f"{s['50']:.1f} / {s['99']:.1f} / {s['max']:.1f} | "
            f"{n['50']:.1f} / {n['99']:.1f} / {n['max']:.1f} | "
            f"{case['n_false_alarms']}/{args.n} |"
        )
    (args.out / "false_alarms.md").write_text("\n".join(lines) + "\n")

    with style():
        fig, axes = new_figure(1, 1, figsize=(7.5, 5.0))
        ax = axes[0, 0]
        colors = {"quiet": BLUE, "moderate": ORANGE, "active": AQUA}
        for regime, sectors in CASES:
            sel = [r for r in rows if r["regime"] == regime and r["n_sectors"] == sectors]
            marker = "o" if sectors == 1 else "s"
            ax.plot(
                [r["sde"] for r in sel],
                [r["snr"] for r in sel],
                marker,
                ms=4.5,
                color=colors[regime],
                mec="white",
                mew=0.6,
                alpha=0.9,
                label=f"{regime}, {sectors} sector{'s' if sectors > 1 else ''}",
            )
        ax.axvline(cfg.sde_threshold, color=INK_MUTED, lw=1)
        ax.axhline(cfg.snr_threshold, color=INK_MUTED, lw=1)
        ax.text(
            cfg.sde_threshold,
            ax.get_ylim()[1],
            " detection region →",
            va="top",
            color=INK_MUTED,
            fontsize=8,
        )
        ax.set_xlabel("SDE of strongest peak")
        ax.set_ylabel("red-noise S/N of strongest peak")
        ax.set_title("Top BLS peak in noise-only light curves", loc="left")
        ax.legend(loc="upper left")
        save_figure(fig, args.out / "false_alarms.png")
    print("\n".join(lines))
    print(f"runtime {elapsed:.0f} s")


if __name__ == "__main__":
    main()
