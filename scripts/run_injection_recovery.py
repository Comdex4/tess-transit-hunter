#!/usr/bin/env python
"""Injection-recovery completeness over a period x radius grid.

Base light curve (the flux *before* detrending) is either

* a real SPOC 2-minute light curve: ``--tic <ID> [--sectors ...]`` (needs MAST access;
  known planets can be masked with ``--mask P,T0,DURATION`` in days/BTJD), or
* a synthetic TESS-like light curve: ``--synthetic`` (offline).

Each injection is detrended and searched exactly like a real target, in parallel.
Results are appended to injections.csv as they complete, so an interrupted run can
be resumed with the same command.

Outputs (in --out): injections.csv, completeness.json, completeness.md,
completeness.png, base_lightcurve.json.
"""

from __future__ import annotations

import argparse
import logging
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from transit_hunter.detrend import DetrendConfig, detrend, ephemeris_mask
from transit_hunter.inject import (
    InjectionGrid,
    RecoveryCriteria,
    completeness,
    completeness_markdown,
    draw_injections,
    plot_completeness,
    run_injections,
)
from transit_hunter.search import SearchConfig, default_n_workers
from transit_hunter.synthetic import NoiseModel, SyntheticStar, simulate_lightcurve
from transit_hunter.utils import binned_rms, write_json

#: Noise properties of the synthetic base light curve (ppm, days).
SYNTHETIC_NOISE = NoiseModel(
    white_ppm=700.0, red_ppm=60.0, red_timescale=0.04, rotation_ppm=1500.0, rotation_period=10.0
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--tic", type=int, help="real target (TIC ID)")
    source.add_argument("--synthetic", action="store_true", help="synthetic base light curve")
    parser.add_argument(
        "--sectors",
        type=int,
        nargs="*",
        default=None,
        help="real data: sectors to use; synthetic: number of sectors (one value)",
    )
    parser.add_argument(
        "--mask-known",
        action="store_true",
        help="real data: mask the star's confirmed transiting planets (NASA Exoplanet Archive)",
    )
    parser.add_argument(
        "--mask",
        action="append",
        default=[],
        help="known transit to mask, 'P,T0,DURATION' (repeatable)",
    )
    parser.add_argument("--periods", type=float, nargs=2, default=(0.5, 20.0))
    parser.add_argument("--n-periods", type=int, default=8)
    parser.add_argument("--radii", type=float, nargs=2, default=(0.7, 8.0))
    parser.add_argument("--n-radii", type=int, default=8)
    parser.add_argument("--per-cell", type=int, default=32)
    parser.add_argument("--seed", type=int, default=2024)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    args.out.mkdir(parents=True, exist_ok=True)

    if args.synthetic:
        n_sectors = args.sectors[0] if args.sectors else 2
        star = SyntheticStar(radius=1.0, mass=1.0, teff=5770.0)
        lc = simulate_lightcurve(star, SYNTHETIC_NOISE, (), n_sectors=n_sectors, seed=args.seed)
        r_star, m_star = star.radius, star.mass
        base_info = {
            "source": "synthetic",
            "n_sectors": n_sectors,
            "star": star.__dict__,
            "noise_model": asdict(SYNTHETIC_NOISE),
            "seed": args.seed,
        }
    else:
        from transit_hunter.catalog import get_stellar_params
        from transit_hunter.data import fetch_lightcurve

        lc = fetch_lightcurve(args.tic, cache_dir=args.cache_dir, sectors=args.sectors)
        stellar = get_stellar_params(args.tic, lc.meta.get("stellar_header"))
        if not (stellar.radius and stellar.mass):
            raise SystemExit("stellar radius and mass are needed to convert injections")
        r_star, m_star = stellar.radius, stellar.mass
        base_info = {
            "source": f"TIC {args.tic}",
            "sectors": lc.sectors,
            "stellar": stellar.as_dict(),
        }

    mask = None
    ephemerides = [tuple(float(x) for x in m.split(",")) for m in args.mask]
    if args.mask_known and args.tic:
        from transit_hunter.catalog import known_ephemerides, query_known_planets_for_tic

        ephemerides += known_ephemerides(query_known_planets_for_tic(args.tic))
    if ephemerides:
        mask = ephemeris_mask(lc.time, ephemerides, width_factor=2.0)
        base_info["masked_ephemerides"] = ephemerides

    flat = detrend(lc if mask is None else lc.select(~mask), DetrendConfig()).flat
    base_info.update(
        n_points=len(lc),
        baseline_days=lc.baseline,
        cdpp_ppm={
            f"{h:g}h": binned_rms(flat.time, flat.flux, h / 24) * 1e6 for h in (0.5, 1.0, 2.0)
        },
    )
    write_json(args.out / "base_lightcurve.json", base_info)

    grid = InjectionGrid.log_spaced(
        tuple(args.periods), args.n_periods, tuple(args.radii), args.n_radii, args.per_cell
    )
    injections = draw_injections(grid, r_star, m_star, t_start=float(lc.time[0]), seed=args.seed)
    search_cfg = SearchConfig(max_signals=2, stellar_density=m_star / r_star**3)
    detrend_cfg = DetrendConfig()
    criteria = RecoveryCriteria()
    start = time.time()
    rows = run_injections(
        lc,
        injections,
        args.out / "injections.csv",
        detrend_cfg,
        search_cfg,
        criteria,
        mask,
        n_workers=args.workers or default_n_workers(),
    )
    elapsed = time.time() - start

    table = completeness(rows, grid)
    summary = table.as_dict()
    summary.update(
        base_lightcurve=base_info,
        recovery_criteria=asdict(criteria),
        search=asdict(search_cfg),
        detrend=asdict(detrend_cfg),
        n_aliases=int(table.aliases.sum()),
        wall_time_s_this_session=elapsed,
        mean_cpu_s_per_injection=float(np.mean([r["runtime_s"] for r in rows])),
    )
    write_json(args.out / "completeness.json", summary)
    (args.out / "completeness.md").write_text(completeness_markdown(table))
    title = "Synthetic TESS-like G dwarf" if args.synthetic else f"TIC {args.tic}"
    plot_completeness(table, args.out / "completeness.png", title=title)
    print(completeness_markdown(table))
    print(f"overall recovery {100 * table.overall:.1f}% of {int(table.total.sum())} injections")


if __name__ == "__main__":
    main()
