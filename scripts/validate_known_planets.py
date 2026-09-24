#!/usr/bin/env python
"""Validate the pipeline on confirmed TESS planets.

For every host in ``transit_hunter.validation.DEFAULT_TARGETS`` this script

1. queries the NASA Exoplanet Archive (``pscomppars``) for its transiting planets,
2. downloads and cleans all SPOC 2-minute sectors (cached),
3. runs the full pipeline (detrend, iterative BLS, MCMC fit, vetting),
4. matches detections to the published planets and writes a comparison table.

Requires network access to exoplanetarchive.ipac.caltech.edu and mast.stsci.edu.

Outputs (in --out): one report folder per host, validation.json, validation.md,
validation_errors.png.

Example::

    python scripts/validate_known_planets.py --workers 8
"""

from __future__ import annotations

import argparse
import logging
import time
from dataclasses import replace
from pathlib import Path

from transit_hunter.catalog import get_stellar_params, query_confirmed_planets
from transit_hunter.data import fetch_lightcurve
from transit_hunter.fit import FitConfig
from transit_hunter.pipeline import PipelineConfig, run_on_lightcurve
from transit_hunter.search import default_n_workers
from transit_hunter.utils import write_json
from transit_hunter.validation import (
    DEFAULT_TARGETS,
    compare_planet,
    comparison_markdown,
    plot_comparison,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=Path("results/validation"))
    parser.add_argument(
        "--hosts",
        nargs="*",
        default=None,
        help="subset of hosts (archive spelling), default: all targets",
    )
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument("--quick", action="store_true", help="short MCMC chains")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    targets = [t for t in DEFAULT_TARGETS if args.hosts is None or t.host in args.hosts]
    workers = args.workers or default_n_workers()
    config = PipelineConfig()
    fit = FitConfig(n_workers=workers)
    if args.quick:
        fit = replace(fit, n_walkers=32, max_steps=3000, min_steps=1000)
    config = replace(config, search=replace(config.search, n_workers=workers), fit=fit)

    published = query_confirmed_planets([t.host for t in targets])
    rows, hosts = [], []
    for target in targets:
        planets = sorted(
            (p for p in published if p.host == target.host), key=lambda p: p.period or 0.0
        )
        if not planets:
            print(f"{target.host}: no transiting planets returned by the archive; skipped")
            continue
        tic = next(p.tic_id for p in planets if p.tic_id)
        start = time.time()
        lc = fetch_lightcurve(tic, cache_dir=args.cache_dir, config=config.cleaning)
        stellar = get_stellar_params(tic, lc.meta.get("stellar_header"))
        folder = args.out / target.host.replace(" ", "_")
        report = run_on_lightcurve(lc, folder, stellar, config, name=target.host)
        host_rows = [compare_planet(p, report) for p in planets]
        rows.extend(host_rows)
        hosts.append(
            {
                "host": target.host,
                "note": target.note,
                "tic_id": tic,
                "sectors": lc.sectors,
                "n_points": len(lc),
                "baseline_days": lc.baseline,
                "stellar": stellar.as_dict(),
                "published": [p.as_dict() for p in planets],
                "report_folder": str(folder),
                "runtime_s": time.time() - start,
            }
        )
        print(
            f"{target.host}: {sum(r['recovered'] for r in host_rows)}/{len(host_rows)} "
            f"planets recovered ({time.time() - start:.0f} s)"
        )

    write_json(args.out / "validation.json", {"hosts": hosts, "comparison": rows})
    (args.out / "validation.md").write_text(comparison_markdown(rows))
    plot_comparison(rows, args.out / "validation_errors.png")
    print(comparison_markdown(rows))


if __name__ == "__main__":
    main()
