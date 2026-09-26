#!/usr/bin/env python
"""Were the confirmed planets that the validation missed in the data at all?

For every planet in ``validation.json`` that the pipeline did not recover, this
script rebuilds the light curve of its host's last search iteration (detrended
with every detection masked, and those detections' transits removed) and
measures, at the planet's published ephemeris, the box depth and the red-noise
S/N exactly as the search computes them. A missed planet with an S/N well above
the detection threshold was in the data; the search failed to pick it out.

The published mid-time is moved to the epoch nearest the middle of the data;
an error in the published period then shifts the transits by at most half the
baseline times that error.

Needs the cached light curves (or network access to mast.stsci.edu).

Example::

    python scripts/check_missed_planets.py --validation results/validation

Writes ``missed_planets.json`` and ``missed_planets.md`` into that folder.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from astropy.timeseries import BoxLeastSquares

from transit_hunter.data import fetch_lightcurve
from transit_hunter.detrend import DetrendConfig, detrend, ephemeris_mask
from transit_hunter.search import count_transits_with_data, red_noise_snr
from transit_hunter.utils import write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--validation", type=Path, default=Path("results/validation"))
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args()

    validation = json.loads((args.validation / "validation.json").read_text())
    hosts = {h["tic_id"]: h for h in validation["hosts"]}
    rows = []
    for missed in (r for r in validation["comparison"] if not r["recovered"]):
        host = hosts[missed["tic_id"]]
        planet = next(p for p in host["published"] if p["name"] == missed["planet"])
        if not (planet["period"] and planet["t0_btjd"] and planet["duration_hours"]):
            print(f"{missed['planet']}: incomplete published ephemeris; skipped")
            continue
        report = json.loads((Path(host["report_folder"]) / "report.json").read_text())
        lc = fetch_lightcurve(host["tic_id"], cache_dir=args.cache_dir)
        width = report["config"]["mask_width_factor"]
        detections = [
            (s["period"], s["t0"], s["duration"])
            for s in report["search"]["signals"]
            if s["detected"]
        ]
        mask = ephemeris_mask(lc.time, detections, width)
        flat = detrend(lc, DetrendConfig(**report["config"]["detrend"]), mask=mask).flat
        flat = flat.select(~ephemeris_mask(flat.time, detections, width))

        period, duration = planet["period"], planet["duration_hours"] / 24.0
        t0 = planet["t0_btjd"]
        t0 += np.round((np.median(flat.time) - t0) / period) * period
        stats = BoxLeastSquares(flat.time, flat.flux, flat.flux_err).compute_stats(
            period, duration, t0
        )
        depth = float(stats["depth"][0])
        n_transits = count_transits_with_data(flat.time, period, t0, duration)
        snr = red_noise_snr(flat, period, t0, duration, depth, n_transits)
        last = report["search"]["signals"][-1]  # the pass that ended the search
        rows.append(
            {
                "planet": missed["planet"],
                "host": host["host"],
                "period": period,
                "t0_btjd": t0,
                "duration_hours": planet["duration_hours"],
                "published_depth_ppm": missed.get("depth_pub_ppm"),
                "box_depth_ppm": depth * 1e6,
                "n_transits_with_data": n_transits,
                "snr": snr,
                "snr_threshold": last["snr_threshold"],
                "search_stopped_at": {
                    "iteration": last["iteration"],
                    "period": last["period"],
                    "sde": last["sde"],
                    "snr": last["snr"],
                },
            }
        )
        print(f"{missed['planet']}: S/N {snr:.1f} at the published ephemeris")

    write_json(args.validation / "missed_planets.json", {"planets": rows})
    lines = [
        "| planet | P (d) | published depth (ppm) | box depth at the published ephemeris (ppm) | "
        "transits with data | red-noise S/N (threshold) | search stopped at |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        stop = r["search_stopped_at"]
        published = r["published_depth_ppm"]
        lines.append(
            f"| {r['planet']} | {r['period']:.5f} | "
            f"{'–' if published is None else f'{published:.0f}'} | {r['box_depth_ppm']:.0f} | "
            f"{r['n_transits_with_data']} | {r['snr']:.1f} ({r['snr_threshold']:.2f}) | "
            f"pass {stop['iteration']}: "
            f"P = {stop['period']:.2f} d, SDE {stop['sde']:.1f} |"
        )
    (args.validation / "missed_planets.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
