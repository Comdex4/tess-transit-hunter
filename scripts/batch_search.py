#!/usr/bin/env python
"""Search many stars for transiting planets and rank what survives.

Three steps, each safe to stop and repeat (see ``transit_hunter.batch``):

    python scripts/batch_search.py select --out runs/mdwarfs --sectors 1-26 \\
        --min-sectors 2 --teff-max 3900 --tmag-max 13 --n 500
    python scripts/batch_search.py run --out runs/mdwarfs --max-hours 9
    python scripts/batch_search.py summarize --out runs/mdwarfs

``select`` writes ``targets.csv`` and downloads the catalogs of confirmed
planets, TOIs and Community TOIs (``catalogs.json``). ``run`` searches every
star not finished yet, one report folder per star under ``stars/``, and
rewrites the summary every 25 stars; stopping it (Ctrl+C) and starting it again
loses at most the star in progress. ``summarize`` screens the candidates found
so far and writes ``candidates.md``, ``candidates.csv``, ``stars.csv`` and
``summary.json``; it can run while ``run`` is going.

Requires network access to mast.stsci.edu, exoplanetarchive.ipac.caltech.edu
and exofop.ipac.caltech.edu.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from dataclasses import asdict, replace
from pathlib import Path

from transit_hunter import __version__
from transit_hunter.batch import (
    KnownCatalog,
    ScreenConfig,
    Selection,
    choose_sectors,
    fetch_known_catalog,
    load_or_fetch_catalog,
    parse_sectors,
    read_targets,
    run_batch,
    sector_targets,
    select_targets,
    summarize_batch,
    write_targets,
)
from transit_hunter.data import default_cache_dir
from transit_hunter.fit import FitConfig
from transit_hunter.pipeline import PipelineConfig
from transit_hunter.search import default_n_workers
from transit_hunter.terminal import banner, is_interactive, use_color, use_unicode
from transit_hunter.utils import write_json


def rough_time(n_sectors: list[int]) -> str:
    """Rough run time on 4 cores for stars without detections: download, detrending
    and two BLS passes (measured: 5-14 s for a 2-sector star). Detections add their fits."""
    seconds = sum(3 + 2.5 * n + 1.2 * n**1.5 for n in n_sectors)
    return f"{seconds / 60:.0f} min" if seconds < 5400 else f"{seconds / 3600:.1f} h"


def selection_text(out: Path) -> str:
    path = out / "selection.json"
    return json.loads(path.read_text()).get("description", "") if path.exists() else ""


def catalog_for(out: Path, refresh: bool = False) -> KnownCatalog:
    return load_or_fetch_catalog(out / "catalogs.json", refresh=refresh)


def cmd_select(args: argparse.Namespace) -> None:
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    selection = Selection(
        sectors=parse_sectors(args.sectors) if args.sectors else [],
        min_sectors=args.min_sectors,
        tmag_max=args.tmag_max,
        tmag_min=args.tmag_min,
        teff_min=args.teff_min,
        teff_max=args.teff_max,
        lumclass=None if args.lumclass.lower() == "any" else args.lumclass.upper(),
        n=args.n,
        seed=args.seed,
        exclude_known_hosts=not args.include_known_hosts,
    )
    print("Downloading the catalogs of known planets, TOIs and Community TOIs...")
    catalog = fetch_known_catalog()
    catalog.save(out / "catalogs.json")
    if args.tic_file:
        targets = read_targets(args.tic_file)
        description = f"the {len(targets)} stars listed in {args.tic_file.name}"
        if selection.exclude_known_hosts:
            hosts = catalog.hosts()
            targets = [t for t in targets if t.tic_id not in hosts]
            description += "; no confirmed planet and no TOI of any disposition"
    else:
        if not selection.sectors:
            raise SystemExit("give --sectors (e.g. 1-26) or --tic-file")
        lists = args.cache_dir or default_cache_dir()
        targets = select_targets(
            selection,
            catalog.hosts(),
            lambda s: sector_targets(s, Path(lists) / "sector_lists"),
        )
        description = selection.describe()
    write_targets(out / "targets.csv", targets)
    write_json(
        out / "selection.json",
        {"description": description, "selection": asdict(selection), "n_targets": len(targets)},
    )
    print(f"\n{len(targets)} targets written to {out / 'targets.csv'}")
    n_sectors = sorted(len(t.sectors) for t in targets if t.sectors)
    if n_sectors:
        print(
            f"sectors per star: median {n_sectors[len(n_sectors) // 2]}, most {n_sectors[-1]}; "
            f"rough run time on 4 cores: {rough_time(n_sectors)} plus the fits of any detections "
            "(the run prints its own estimate as it goes)"
        )
        print(
            f"download cache: about {2.3 * sum(n_sectors) / 1000:.0f} GB of light curves "
            "(2.3 MB per star and sector), plus 100-400 MB of target-pixel files for each "
            "star with a candidate"
        )
    elif targets:
        print("every available sector of each star will be searched")
    if not catalog.complete:
        print(
            "warning: some catalogs could not be downloaded ("
            + ", ".join(catalog.missing())
            + "); `summarize` tries again, and no candidate is a prospect until they are in"
        )


def cmd_run(args: argparse.Namespace) -> None:
    out: Path = args.out
    targets = read_targets(out / "targets.csv")
    if is_interactive(sys.stdout):
        width = shutil.get_terminal_size((100, 20)).columns
        print("\n" + banner(__version__, use_color(sys.stdout), use_unicode(sys.stdout), width))
    workers = args.workers or default_n_workers()
    config = PipelineConfig()
    fit = FitConfig(n_workers=workers)
    if args.quick_fits:
        fit = replace(fit, n_walkers=32, max_steps=3000, min_steps=1000)
    config = replace(config, search=replace(config.search, n_workers=workers), fit=fit)
    write_json(
        out / "run_settings.json",
        {
            "workers": workers,
            "max_sectors": args.max_sectors,
            "quick_fits": args.quick_fits,
            "max_hours": args.max_hours,
        },
    )
    catalog = catalog_for(out)
    screen = ScreenConfig()
    description = selection_text(out)
    if args.max_sectors:
        longest = max(
            (len(choose_sectors(t.sectors, args.max_sectors) or []) for t in targets), default=0
        )
        print(
            f"searching at most {args.max_sectors} sectors per star, the latest "
            f"(longest here: {longest})"
        )
    counts = run_batch(
        targets,
        out,
        config,
        cache_dir=args.cache_dir,
        max_sectors=args.max_sectors,
        max_hours=args.max_hours,
        retry_failed=args.retry_failed,
        summarize=lambda: summarize_batch(out, catalog, screen, description),
        summarize_every=args.summarize_every,
    )
    print(f"\nthis run: {counts or 'nothing to do'}; tables in {out}/candidates.md")


def cmd_summarize(args: argparse.Namespace) -> None:
    out: Path = args.out
    catalog = catalog_for(out, refresh=args.refresh_catalogs)
    screen = ScreenConfig(
        min_snr=args.min_snr,
        min_sde=args.min_sde,
        min_transits=args.min_transits,
    )
    summary = summarize_batch(out, catalog, screen, selection_text(out))
    stars = sum(summary["stars"].values())
    tiers = ", ".join(f"{v} {k}" for k, v in summary["candidates"].items())
    print(f"{stars} stars processed; candidates: {tiers}")
    print(f"tables: {out / 'candidates.md'}, {out / 'candidates.csv'}, {out / 'stars.csv'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--out", type=Path, required=True, help="folder of this batch")
        p.add_argument(
            "--cache-dir",
            type=Path,
            default=None,
            help="downloaded data (default: ~/.cache/transit_hunter or $TRANSIT_HUNTER_CACHE)",
        )

    select = sub.add_parser("select", help="choose the stars and download the catalogs")
    common(select)
    select.add_argument("--sectors", default=None, help="sectors to draw stars from, e.g. 1-26")
    select.add_argument(
        "--min-sectors", type=int, default=1, help="stars with data in at least this many"
    )
    select.add_argument("--tmag-max", type=float, default=13.0, help="faintest TESS magnitude")
    select.add_argument("--tmag-min", type=float, default=None, help="brightest TESS magnitude")
    select.add_argument("--teff-min", type=float, default=None, help="coolest star (K)")
    select.add_argument("--teff-max", type=float, default=None, help="hottest star (K)")
    select.add_argument(
        "--lumclass", default="DWARF", help="TIC luminosity class, or 'any' (default DWARF)"
    )
    select.add_argument("--n", type=int, default=None, help="number of stars (default: all)")
    select.add_argument("--seed", type=int, default=1, help="random order of the stars")
    select.add_argument(
        "--include-known-hosts",
        action="store_true",
        help="keep stars that already host a confirmed planet or a TOI",
    )
    select.add_argument(
        "--tic-file", type=Path, default=None, help="use these TIC IDs (one per line) instead"
    )
    select.set_defaults(func=cmd_select)

    run = sub.add_parser("run", help="search every star not finished yet")
    common(run)
    run.add_argument("--workers", type=int, default=None, help="processes (default: all cores)")
    run.add_argument(
        "--max-sectors",
        type=int,
        default=None,
        help="search at most this many sectors per star, the latest (default: all selected)",
    )
    run.add_argument(
        "--max-hours", type=float, default=None, help="stop after this long; run again to go on"
    )
    run.add_argument(
        "--retry-failed", action="store_true", help="try stars that failed or found no data again"
    )
    run.add_argument(
        "--quick-fits",
        action="store_true",
        help="short MCMC chains (faster; re-run prospects with full fits)",
    )
    run.add_argument(
        "--summarize-every", type=int, default=25, help="rewrite the tables every N stars"
    )
    run.set_defaults(func=cmd_run)

    summarize = sub.add_parser("summarize", help="screen and rank the candidates found so far")
    common(summarize)
    screen = ScreenConfig()
    summarize.add_argument("--min-snr", type=float, default=screen.min_snr)
    summarize.add_argument("--min-sde", type=float, default=screen.min_sde)
    summarize.add_argument("--min-transits", type=int, default=screen.min_transits)
    summarize.add_argument(
        "--refresh-catalogs", action="store_true", help="download the catalogs again"
    )
    summarize.set_defaults(func=cmd_summarize)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(level=logging.WARNING)
    try:
        args.func(args)
    except KeyboardInterrupt:
        kept = "; finished stars are kept, and the same command continues"
        print(f"\nstopped{kept if args.command == 'run' else ''}", file=sys.stderr)
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
