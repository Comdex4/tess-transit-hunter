#!/usr/bin/env python
"""Transit-timing diagnostic for one candidate of a pipeline report.

The pipeline folds every signal on a single period, so transit-timing variations
(TTVs), for example of a planet in a pair near a mean-motion resonance, are not
modelled. For one candidate this script rebuilds the light curve the pipeline
vetted (detrended with every detection masked; the other detections' transits
removed), measures the mid-time of every fully covered transit with the fitted
transit shape held fixed, and compares the times with a linear ephemeris
(O - C), also as medians per observing season. The timing uncertainties include
white noise only and are lower limits.

Needs the cached light curve (or network access to mast.stsci.edu).

Example::

    python scripts/transit_timing.py --report results/validation/TOI-270 --candidate 2

Writes ``timing_<n>.json``, ``timing_<n>.md`` and ``timing_<n>.png`` into the
report folder.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from transit_hunter.data import fetch_lightcurve
from transit_hunter.detrend import DetrendConfig, detrend, ephemeris_mask
from transit_hunter.lightcurve import LightCurve
from transit_hunter.models import TransitParams, q_to_u
from transit_hunter.plotting import BLUE, INK, INK_MUTED, new_figure, save_figure, style
from transit_hunter.utils import write_json
from transit_hunter.vet import (
    VetConfig,
    measure_transit_times,
    template_from_params,
    transit_coverage,
)

#: Transits separated by more than this many days belong to different observing seasons.
SEASON_GAP = 100.0


def vetted_light_curve(report: dict, candidate: dict, lc: LightCurve) -> LightCurve:
    """The light curve the pipeline vetted this candidate on (see pipeline.py)."""
    signals = report["search"]["signals"]
    detections = [s for s in signals if s["detected"]]
    width = report["config"]["mask_width_factor"]
    eph = [(s["period"], s["t0"], s["duration"]) for s in detections]
    flat = detrend(
        lc, DetrendConfig(**report["config"]["detrend"]), mask=ephemeris_mask(lc.time, eph, width)
    ).flat
    own = candidate["signal"]["iteration"] - 1
    others = [
        (s["period"], s["t0"], s["duration"])
        for i, s in enumerate(detections)
        if s["iteration"] - 1 != own and s.get("secondary_of") != own
    ]
    return flat.select(~ephemeris_mask(flat.time, others, width)) if others else flat


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--report", type=Path, required=True, help="pipeline report folder")
    parser.add_argument("--candidate", type=int, default=1, help="candidate number (1-based)")
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args()

    report = json.loads((args.report / "report.json").read_text())
    candidates = [p for p in report["planets"] if p["role"] == "candidate"]
    candidate = candidates[args.candidate - 1]
    fit = candidate["fit"]
    best = fit["max_posterior_sample"]
    period, t0 = best["period"], best["t0"]
    duration = fit["posterior"]["t14_hours"]["median"] / 24.0
    u1, u2 = q_to_u(best["q1"], best["q2"])
    shape = TransitParams(t0, period, best["rp_rs"], math.exp(best["ln_a_rs"]), best["b"], u1, u2)

    target = report["target"]
    lc = fetch_lightcurve(target["tic_id"], cache_dir=args.cache_dir)
    vetted = vetted_light_curve(report, candidate, lc)

    # 2. transit times of the fully covered transits
    config = VetConfig()
    epochs = [
        e
        for e in transit_coverage(vetted, period, t0, duration)
        if e["inside"] >= config.coverage_min and e["before"] >= 0.5 and e["after"] >= 0.5
    ]
    times = measure_transit_times(vetted, period, t0, duration, template_from_params(shape), epochs)
    epoch = np.array([x["epoch"] for x in times], dtype=float)
    tc = np.array([x["tc"] for x in times])
    err = np.array([x["err"] for x in times])
    coeffs = np.polyfit(epoch, tc, 1, w=1.0 / err)
    oc = (tc - np.polyval(coeffs, epoch)) * 1440.0
    season = np.concatenate([[0], np.cumsum(np.diff(tc) > SEASON_GAP)])
    seasons = []
    for s in np.unique(season):
        sel = season == s
        seasons.append(
            {
                "first_btjd": float(tc[sel].min()),
                "last_btjd": float(tc[sel].max()),
                "n_transits": int(sel.sum()),
                "median_o_minus_c_min": float(np.median(oc[sel])),
            }
        )

    name = f"{target['name']} candidate {args.candidate}"
    out = {
        "target": target["name"],
        "candidate": args.candidate,
        "period": period,
        "t14_hours_from_fit": duration * 24.0,
        "n_transits_timed": len(times),
        "o_minus_c": [
            {"epoch": int(e), "tc_btjd": float(t), "o_minus_c_min": float(o), "err_min": float(s)}
            for e, t, o, s in zip(epoch, tc, oc, err * 1440.0, strict=True)
        ],
        "seasons": seasons,
        "chi2_linear": float(np.sum((oc / (err * 1440.0)) ** 2)),
        "dof": len(times) - 2,
        "note": "timing uncertainties exclude correlated noise and are lower limits",
    }
    stem = args.report / f"timing_{args.candidate}"
    write_json(stem.with_suffix(".json"), out)

    lines = [
        f"Transit times of {name} (P = {period:.5f} d), measured with the fitted shape held "
        f"fixed: {len(times)} fully covered transits. Timing uncertainties exclude correlated "
        "noise and are lower limits.",
        "",
        "| observing season (BTJD) | transits | median O − C (min) |",
        "|---|---|---|",
    ]
    for s in seasons:
        lines.append(
            f"| {s['first_btjd']:.0f}–{s['last_btjd']:.0f} | {s['n_transits']} | "
            f"{s['median_o_minus_c_min']:+.1f} |"
        )
    stem.with_suffix(".md").write_text("\n".join(lines) + "\n")

    with style():
        fig, axes = new_figure(1, 1, figsize=(8.0, 3.6))
        ax = axes[0, 0]
        ax.errorbar(
            epoch,
            oc,
            yerr=err * 1440.0,
            fmt="o",
            ms=5,
            color=BLUE,
            mec="white",
            mew=0.8,
            elinewidth=1.4,
            capsize=0,
            label="transit time",
        )
        for s in seasons:
            sel = (tc >= s["first_btjd"]) & (tc <= s["last_btjd"])
            ax.plot(
                [epoch[sel].min(), epoch[sel].max()],
                [s["median_o_minus_c_min"]] * 2,
                color=INK_MUTED,
                lw=2.0,
                label="season median" if s is seasons[0] else None,
            )
        ax.axhline(0.0, color=INK, lw=0.9)
        ax.set_xlabel("transit number")
        ax.set_ylabel("observed − linear ephemeris (min)")
        ax.set_title(f"{name}: transit times", loc="left")
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), borderaxespad=0.0)
        save_figure(fig, stem.with_suffix(".png"))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
