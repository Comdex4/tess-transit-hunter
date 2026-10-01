#!/usr/bin/env python
"""Run the momentum-dump vetting test on the stored real-data results.

The test (:func:`transit_hunter.vet.momentum_dump_test`) needs the times of
TESS's momentum dumps, which processed light curves record since cache format 2,
so it is not in the reports made before it existed. This script re-processes the
light curves of the resolved TOIs (``results/toi_calibration``) and of the known
planets (``results/validation``) from the download cache, takes each candidate's
ephemeris from its stored report (the fit's where there is one, as in the
pipeline), masks the other detections and applies the test, which needs no fit.
Confirmed planets should pass. Writes ``results/calibration/momentum_dumps.json``
and ``.md``.

Requires network access to mast.stsci.edu (to search for the light curves; files
already downloaded are not fetched again).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from transit_hunter.data import fetch_lightcurve
from transit_hunter.detrend import DetrendConfig, detrend, ephemeris_mask
from transit_hunter.pipeline import PipelineConfig
from transit_hunter.utils import write_json
from transit_hunter.vet import bad_transits, momentum_dump_test, without_transits

ROOT = Path(__file__).resolve().parents[1]


def ephemeris(entry: dict[str, Any]) -> tuple[float, float, float]:
    """Period, mid-transit time and duration (days) the vetting used."""
    sig = entry["signal"]
    post = entry.get("fit", {}).get("posterior", {})
    if "period" in post and "t0" in post and "t14_hours" in post:
        return post["period"]["median"], post["t0"]["median"], post["t14_hours"]["median"] / 24
    return sig["period"], sig["t0"], sig["duration"]


def check(report_path: Path, iteration: int) -> dict[str, Any]:
    """The dump test for candidate ``iteration`` of a stored report."""
    report = json.loads(report_path.read_text())
    target = report["target"]
    entry = next(p for p in report["planets"] if p["signal"]["iteration"] == iteration)
    period, t0, duration = ephemeris(entry)
    detected = [
        (s["period"], s["t0"], s["duration"]) for s in report["search"]["signals"] if s["detected"]
    ]
    others = [
        (s["period"], s["t0"], s["duration"])
        for s in report["search"]["signals"]
        if s["detected"] and s["iteration"] != iteration
    ]
    lc = fetch_lightcurve(target["tic_id"], sectors=target["sectors"])
    width = PipelineConfig().mask_width_factor
    flat = detrend(
        lc,
        DetrendConfig(**report["config"]["detrend"]),
        mask=ephemeris_mask(lc.time, detected, width_factor=width),
    ).flat
    planet_lc = flat.select(~ephemeris_mask(flat.time, others, width_factor=width))
    # as in the pipeline, a single transit far from the others' depth is left out first
    dropped, _ = bad_transits(planet_lc, period, t0, duration)
    if dropped:
        planet_lc = without_transits(planet_lc, [x["tc"] for x in dropped], duration)
    result = momentum_dump_test(planet_lc, period, t0, duration)
    return {
        "tic_id": target["tic_id"],
        "sectors": target["sectors"],
        "period": period,
        "n_dumps": len(lc.meta.get("momentum_dumps", [])),
        "status": result.status if result else "not run",
        "message": result.message if result else "no dump times",
        "dropped_transits": [round(x["tc"], 4) for x in dropped],
        "verdict_before": entry["vetting"]["verdict"],
    }


def toi_cases() -> list[dict[str, Any]]:
    calibration = json.loads((ROOT / "results/toi_calibration/calibration.json").read_text())
    cases = []
    for toi in calibration["tois"]:
        if not toi.get("recovered"):
            continue
        report_path = ROOT / toi["report_folder"] / "report.json"
        report = json.loads(report_path.read_text())
        # the candidate the calibration matched to the TOI (perhaps at a multiple of its period)
        wanted = toi["catalog"]["period"] * toi.get("period_ratio", 1.0)
        entry = min(report["planets"], key=lambda p: abs(p["signal"]["period"] - wanted))
        cases.append(
            {
                "name": toi["toi"],
                "class": toi["class"],
                "disposition": toi["disposition"],
                "report": report_path,
                "iteration": entry["signal"]["iteration"],
            }
        )
    return cases


def planet_cases() -> list[dict[str, Any]]:
    validation = json.loads((ROOT / "results/validation/validation.json").read_text())
    cases = []
    for host in validation["hosts"]:
        for det in host["detections"]:
            if det["role"] == "candidate" and det["matches"]:
                cases.append(
                    {
                        "name": det["matches"],
                        "class": "planet",
                        "disposition": "confirmed",
                        "report": ROOT / host["report_folder"] / "report.json",
                        "iteration": det["iteration"],
                    }
                )
    return cases


def markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Momentum-dump test on the stored real-data results",
        "",
        "Generated by `scripts/check_momentum_dumps.py`.",
        "",
        "| object | class | P (d) | dumps in the data | result | verdict before the test |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['name']} | {r['class']} ({r['disposition']}) | {r['period']:.5f} | "
            f"{r['n_dumps']} | [{r['status']}] {r['message']} | {r['verdict_before']} |"
        )
    counts: dict[str, dict[str, int]] = {}
    for r in rows:
        counts.setdefault(r["class"], {}).setdefault(r["status"], 0)
        counts[r["class"]][r["status"]] += 1
    summary = "; ".join(
        f"{c}: " + ", ".join(f"{n} {s}" for s, n in sorted(v.items())) for c, v in counts.items()
    )
    lines += ["", f"Summary: {summary}.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=ROOT / "results/calibration")
    args = parser.parse_args()
    rows = []
    for case in [*planet_cases(), *toi_cases()]:
        try:
            result = check(case["report"], case["iteration"])
        except Exception as exc:  # one unavailable light curve must not stop the rest
            result = {
                "period": float("nan"),
                "n_dumps": 0,
                "status": "error",
                "message": f"{type(exc).__name__}: {exc}",
                "verdict_before": "",
            }
        row = {k: v for k, v in case.items() if k != "report"} | result
        print(
            f"{row['name']:16s} {row['class']:15s} [{row['status']}] {row['message']}", flush=True
        )
        rows.append(row)
    args.out.mkdir(parents=True, exist_ok=True)
    write_json(args.out / "momentum_dumps.json", rows)
    (args.out / "momentum_dumps.md").write_text(markdown(rows))


if __name__ == "__main__":
    main()
