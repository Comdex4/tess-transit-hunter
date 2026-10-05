#!/usr/bin/env python
"""Transit-by-transit diagnostic for one candidate of a pipeline report: times and depths.

The pipeline folds every signal on a single period, so anything that varies from
transit to transit is averaged away. For one candidate this script rebuilds the
light curve the pipeline vetted (detrended with every detection masked; the other
detections' transits removed) and, for every fully covered transit,

* measures the mid-time with the fitted transit shape held fixed and compares
  it with a linear ephemeris (O - C), also as medians per observing season.
  Transit-timing variations (TTVs), for example of a planet in a pair near a
  mean-motion resonance, are not modeled by the pipeline. The timing
  uncertainties include white noise only and are lower limits;
* measures the depth (the flanks' median minus the median of the central 70 %
  of the transit) and the change of the out-of-transit level across the
  transit (:func:`transit_hunter.vet.transit_depths`). A transit on an
  instrumental ramp stands out in both, and a single such transit can bias the
  odd/even comparison or the fitted shape. Transits are flagged by the same
  rule the pipeline uses to leave them out before the fit and the vetting
  (:func:`transit_hunter.vet.bad_transits`), and the odd/even test is shown
  with and without them.

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
from transit_hunter.models import TransitParams, q_to_u, transit_model
from transit_hunter.plotting import BLUE, INK, INK_MUTED, ORANGE, new_figure, save_figure, style
from transit_hunter.search import without_events
from transit_hunter.utils import write_json
from transit_hunter.vet import (
    VetConfig,
    bad_transits,
    measure_transit_times,
    odd_even_test,
    template_from_params,
    transit_coverage,
    transit_depths,
    without_transits,
)

#: Transits separated by more than this many days belong to different observing seasons.
SEASON_GAP = 100.0


def candidate_light_curve(report: dict, candidate: dict, lc: LightCurve) -> LightCurve:
    """The candidate's light curve in the pipeline, before any transit is left out.

    Detrended with every detection masked, then without the dips the search set
    aside at the edges of the data and without the other detections' transits
    (see pipeline.py).
    """
    signals = report["search"]["signals"]
    detections = [s for s in signals if s["detected"]]
    width = report["config"]["mask_width_factor"]
    eph = [(s["period"], s["t0"], s["duration"]) for s in detections]
    flat = detrend(
        lc, DetrendConfig(**report["config"]["detrend"]), mask=ephemeris_mask(lc.time, eph, width)
    ).flat
    passes = report["search"].get("passes", [])
    events = list({round(e["time"], 4): e for p in passes for e in p["edge_events"]}.values())
    flat = without_events(flat, events, report["config"]["search"]["mask_factor"])
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
    vetted = candidate_light_curve(report, candidate, lc)

    # 1. the fully covered transits
    config = VetConfig()
    epochs = [
        e
        for e in transit_coverage(vetted, period, t0, duration)
        if e["inside"] >= config.coverage_min and e["before"] >= 0.5 and e["after"] >= 0.5
    ]

    # 2. their mid-times (O - C against a linear ephemeris), overall and per season
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

    # 3. their depths, with the pipeline's rule for transits far from the others
    depths = {d["epoch"]: d for d in transit_depths(vetted, period, t0, duration)}
    flagged, stats = bad_transits(vetted, period, t0, duration, config)
    flagged_epochs = {x["epoch"] for x in flagged}
    median_depth = stats.get("median_depth", float("nan")) * 1e6
    scale = stats.get("scale", float("nan")) * 1e6
    timing = {int(e): (float(o), float(s)) for e, o, s in zip(epoch, oc, err * 1440.0, strict=True)}
    transits = []
    for e in epochs:
        d = depths.get(e["epoch"])
        o_c, o_c_err = timing.get(e["epoch"], (None, None))
        transits.append(
            {
                "epoch": e["epoch"],
                "parity": "odd" if e["epoch"] % 2 else "even",
                "tc_btjd": e["tc"],
                "depth_ppm": None if d is None else d["depth"] * 1e6,
                "depth_err_ppm": None if d is None else d["depth_err"] * 1e6,
                "pre_minus_post_ppm": None
                if d is None or not math.isfinite(d["step"])
                else d["step"] * 1e6,
                "outlier": e["epoch"] in flagged_epochs,
                "o_minus_c_min": o_c,
                "err_min": o_c_err,
            }
        )

    # 4. the odd/even test with and without the flagged transits
    model = transit_model(vetted.time, shape)
    odd_even = {"all transits": odd_even_test(vetted, period, t0, duration, model)}
    if flagged:
        rest = without_transits(vetted, [x["tc"] for x in flagged], duration)
        odd_even["without the flagged transits"] = odd_even_test(
            rest, period, t0, duration, transit_model(rest.time, shape)
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
        "median_depth_ppm": median_depth,
        "depth_scale_ppm": scale,
        "dropped_by_pipeline_btjd": [x["tc"] for x in candidate.get("dropped_transits", [])],
        "transits": transits,
        "odd_even": {k: {"status": v.status, "message": v.message} for k, v in odd_even.items()},
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
    lines += [
        "",
        f"Transit by transit. Depth: median of the flanks (0.75–2 durations from mid-transit) "
        f"minus the median of the central 70 % of the transit; median {median_depth:.0f} ppm. "
        f"Flagged: depth more than {config.bad_transit_sigma:g} times {scale:.0f} ppm (the "
        "larger of the robust scatter of the depths and their typical uncertainty) from the "
        "median, if no more than a tenth of the transits are (the rule by which the pipeline "
        "leaves transits out before the fit and the vetting).",
        "",
        "| transit | parity | mid-time (BTJD) | depth (ppm) | level before − after (ppm) | "
        "O − C (min) | flagged |",
        "|---|---|---|---|---|---|---|",
    ]
    for x in transits:
        depth = (
            "–" if x["depth_ppm"] is None else f"{x['depth_ppm']:.0f} ± {x['depth_err_ppm']:.0f}"
        )
        step = "–" if x["pre_minus_post_ppm"] is None else f"{x['pre_minus_post_ppm']:+.0f}"
        o_c = "–" if x["o_minus_c_min"] is None else f"{x['o_minus_c_min']:+.1f}"
        lines.append(
            f"| {x['epoch']} | {x['parity']} | {x['tc_btjd']:.3f} | {depth} | {step} | {o_c} | "
            f"{'yes' if x['outlier'] else ''} |"
        )
    lines += ["", "Odd/even test (the pipeline's, with the fitted transit shape):", ""]
    lines += [f"* {label}: [{r.status}] {r.message}" for label, r in odd_even.items()]
    stem.with_suffix(".md").write_text("\n".join(lines) + "\n")

    with style():
        fig, axes = new_figure(2, 1, figsize=(8.0, 6.4), sharex=True)
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
        ax.set_ylabel("observed − linear ephemeris (min)")
        ax.set_title(f"{name}: transit by transit", loc="left")
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), borderaxespad=0.0)

        ax = axes[1, 0]
        shown = [x for x in transits if x["depth_ppm"] is not None]
        for flagged, color, label in ((False, BLUE, "transit depth"), (True, ORANGE, "flagged")):
            sel = [x for x in shown if x["outlier"] == flagged]
            if sel:
                ax.plot(
                    [x["epoch"] for x in sel],
                    [x["depth_ppm"] for x in sel],
                    "o",
                    ms=6,
                    color=color,
                    mec="white",
                    mew=0.8,
                    label=label,
                )
        ax.axhline(median_depth, color=INK_MUTED, lw=2.0, label="median")
        ax.set_xlabel("transit number")
        ax.set_ylabel("depth (ppm)")
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), borderaxespad=0.0)
        save_figure(fig, stem.with_suffix(".png"))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
