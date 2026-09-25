"""Command-line interface: ``transit-hunter run --tic <ID>`` and friends."""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path

from .fit import FitConfig
from .pipeline import PipelineConfig, run_on_lightcurve
from .search import default_n_workers


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("reports"),
        help="parent folder for report folders (default: ./reports)",
    )
    parser.add_argument(
        "--window", type=float, default=0.75, help="detrending window length in days (default 0.75)"
    )
    parser.add_argument("--min-period", type=float, default=0.5, help="days (default 0.5)")
    parser.add_argument(
        "--max-period", type=float, default=None, help="days (default: half the time baseline)"
    )
    parser.add_argument(
        "--max-signals",
        type=int,
        default=5,
        help="maximum iterations of the multi-planet search (default 5)",
    )
    parser.add_argument("--sde", type=float, default=None, help="SDE detection threshold")
    parser.add_argument("--snr", type=float, default=None, help="S/N detection threshold")
    parser.add_argument("--no-fit", action="store_true", help="skip MCMC fitting")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="short MCMC chains (for a first look; check convergence flags)",
    )
    parser.add_argument("--walkers", type=int, default=None, help="emcee walkers")
    parser.add_argument("--max-steps", type=int, default=None, help="maximum MCMC steps")
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="processes for the BLS and MCMC (default: all cores)",
    )
    parser.add_argument("--seed", type=int, default=42, help="random seed for the MCMC")
    parser.add_argument("-v", "--verbose", action="count", default=0)


def _config(args: argparse.Namespace) -> PipelineConfig:
    cfg = PipelineConfig()
    workers = args.workers or default_n_workers()
    search = replace(
        cfg.search,
        min_period=args.min_period,
        max_period=args.max_period,
        max_signals=args.max_signals,
        n_workers=workers,
    )
    if args.sde is not None:
        search = replace(search, sde_threshold=args.sde)
    if args.snr is not None:
        search = replace(search, snr_threshold=args.snr)
    fit = FitConfig(seed=args.seed, n_workers=workers)
    if args.quick:
        fit = replace(fit, n_walkers=32, max_steps=3000, min_steps=1000)
    if args.walkers:
        fit = replace(fit, n_walkers=args.walkers)
    if args.max_steps:
        fit = replace(fit, max_steps=args.max_steps, min_steps=min(fit.min_steps, args.max_steps))
    return replace(
        cfg,
        detrend=replace(cfg.detrend, window_length=args.window),
        search=search,
        fit=fit,
        fit_signals=not args.no_fit,
    )


def cmd_run(args: argparse.Namespace) -> int:
    from .catalog import get_stellar_params
    from .data import fetch_lightcurve

    config = _config(args)
    lc = fetch_lightcurve(
        args.tic,
        cache_dir=args.cache_dir,
        sectors=args.sectors,
        config=config.cleaning,
        force_download=args.refresh,
    )
    stellar = get_stellar_params(args.tic, lc.meta.get("stellar_header"))
    name = args.name or f"TIC {args.tic}"
    outdir = args.outdir / f"TIC{args.tic}"
    report = run_on_lightcurve(lc, outdir, stellar, config, name=name)
    _print_summary(report, outdir)
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    from .data import fetch_lightcurve

    lc = fetch_lightcurve(
        args.tic, cache_dir=args.cache_dir, sectors=args.sectors, force_download=args.refresh
    )
    print(
        f"TIC {args.tic}: {len(lc)} points, sectors {lc.sectors}, cached at "
        f"{lc.meta.get('cache_file')}"
    )
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    """Run the pipeline on a synthetic multi-planet system (no network needed)."""
    from .catalog import StellarParams
    from .synthetic import NoiseModel, SyntheticStar, planet_from_physical, simulate_lightcurve

    star = SyntheticStar(radius=0.45, mass=0.45, teff=3600)
    planets = [
        planet_from_physical(3.36, 1.6, star, t0=2000.9, b=0.2),
        planet_from_physical(5.66, 2.4, star, t0=2002.1, b=0.35),
        planet_from_physical(11.38, 2.2, star, t0=2003.3, b=0.15),
    ]
    noise = NoiseModel(
        white_ppm=900, red_ppm=80, red_timescale=0.05, rotation_ppm=2500, rotation_period=9.0
    )
    lc = simulate_lightcurve(star, noise, planets, n_sectors=args.sectors, seed=args.seed)
    stellar = StellarParams(
        radius=star.radius,
        radius_err=0.02,
        mass=star.mass,
        mass_err=0.02,
        teff=star.teff,
        teff_err=100,
        source="synthetic star (known truth)",
    )
    config = _config(args)
    outdir = args.outdir / "synthetic_demo"
    report = run_on_lightcurve(lc, outdir, stellar, config, name="Synthetic M-dwarf system")
    _print_summary(report, outdir)
    return 0


def _print_summary(report: dict, outdir: Path) -> None:
    print(f"\n{report['target']['name']}: {report['search']['n_detections']} detection(s)")
    for i, planet in enumerate(report["planets"], 1):
        sig = planet["signal"]
        line = f"  {i}. P = {sig['period']:.5f} d, S/N = {sig['snr']:.1f}"
        fit = planet.get("fit")
        if fit and fit["posterior"].get("rp_earth"):
            rp = fit["posterior"]["rp_earth"]
            line += f", Rp = {rp['median']:.2f} R_earth"
        line += f" -> {planet['vetting']['verdict']}"
        print(line)
    print(f"report: {outdir / 'report.json'}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="transit-hunter",
        description="Detect, fit, and vet transiting planets in TESS 2-minute light curves.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="full pipeline for one TIC target (needs MAST access)")
    run.add_argument("--tic", type=int, required=True, help="TESS Input Catalog ID")
    run.add_argument("--name", default=None, help="display name (default 'TIC <ID>')")
    run.add_argument(
        "--sectors",
        type=int,
        nargs="*",
        default=None,
        help="restrict to these sectors (default: all with 2-min data)",
    )
    run.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="data cache (default $TRANSIT_HUNTER_CACHE or ~/.cache/transit_hunter)",
    )
    run.add_argument("--refresh", action="store_true", help="ignore the processed-data cache")
    _add_common(run)
    run.set_defaults(func=cmd_run)

    fetch = sub.add_parser("fetch", help="download, clean, and cache a light curve only")
    fetch.add_argument("--tic", type=int, required=True)
    fetch.add_argument("--sectors", type=int, nargs="*", default=None)
    fetch.add_argument("--cache-dir", type=Path, default=None)
    fetch.add_argument("--refresh", action="store_true")
    fetch.add_argument("-v", "--verbose", action="count", default=0)
    fetch.set_defaults(func=cmd_fetch)

    demo = sub.add_parser("demo", help="pipeline on a synthetic 3-planet system (offline)")
    demo.add_argument("--sectors", type=int, default=3, help="number of simulated sectors")
    _add_common(demo)
    demo.set_defaults(func=cmd_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    import requests

    from .data import NoDataError

    parser = build_parser()
    args = parser.parse_args(argv)
    level = logging.WARNING - 10 * min(args.verbose, 2)
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")
    try:
        return int(args.func(args))
    except NoDataError as exc:
        print(f"transit-hunter: {exc}", file=sys.stderr)
        return 2
    except requests.exceptions.RequestException as exc:
        print(
            "transit-hunter: could not reach the data archive "
            f"({exc.__class__.__name__}: {exc}).\n"
            "Downloading light curves needs network access to mast.stsci.edu; previously "
            "downloaded targets are served from the cache without it.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
