#!/usr/bin/env python
"""End-to-end test of the full pipeline on synthetic systems with known truth.

Runs exactly the pipeline used on real targets (detrend, iterative BLS, MCMC fit,
vetting) on simulated TESS-like light curves and compares the recovered period,
depth, and radius with the injected values, in the same format as the real-planet
validation. It covers the regimes of the real validation sample: a hot Jupiter,
a small planet around a bright star with many sectors, a compact M-dwarf
multi-planet system, and a long-period planet. It also includes an eclipsing binary
detected at half its true period, which vetting should reject.

These are simulations, not TESS data. Parameters are inputs chosen for the test.

Outputs (in --out): one report folder per system, benchmark.json, benchmark.md,
benchmark_errors.png.
"""

from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

from transit_hunter.catalog import PublishedPlanet, StellarParams
from transit_hunter.fit import FitConfig
from transit_hunter.lightcurve import LightCurve
from transit_hunter.models import TransitParams, transit_model
from transit_hunter.pipeline import PipelineConfig, run_on_lightcurve
from transit_hunter.search import default_n_workers
from transit_hunter.synthetic import (
    NoiseModel,
    SyntheticPlanet,
    SyntheticStar,
    planet_from_physical,
    simulate_lightcurve,
)
from transit_hunter.utils import write_json
from transit_hunter.validation import compare_planet, comparison_markdown, plot_comparison


@dataclass
class System:
    name: str
    description: str
    star: SyntheticStar
    noise: NoiseModel
    planets: list[tuple[float, float, float, float]]  # (period, radius_earth, t0, b)
    n_sectors: int
    seed: int
    eclipsing_binary: bool = False
    extra: dict = field(default_factory=dict)


SYSTEMS = [
    System(
        "SYN-1",
        "hot Jupiter on a sub-day orbit around an F star",
        SyntheticStar(radius=1.25, mass=1.25, teff=6400),
        NoiseModel(white_ppm=350, red_ppm=40, rotation_ppm=500, rotation_period=5.0),
        [(0.94, 13.0, 2000.35, 0.35)],
        n_sectors=2,
        seed=101,
    ),
    System(
        "SYN-2",
        "small planet around a bright, quiet G dwarf observed for six sectors",
        SyntheticStar(radius=1.1, mass=1.1, teff=6000),
        NoiseModel(white_ppm=200, red_ppm=30, rotation_ppm=300, rotation_period=18.0),
        [(6.27, 2.0, 2002.1, 0.5)],
        n_sectors=6,
        seed=102,
    ),
    System(
        "SYN-3",
        "compact three-planet system around an M dwarf",
        SyntheticStar(radius=0.38, mass=0.39, teff=3500),
        NoiseModel(white_ppm=1100, red_ppm=80, rotation_ppm=2000, rotation_period=15.0),
        [(3.36, 1.3, 2000.8, 0.2), (5.66, 2.4, 2002.4, 0.3), (11.38, 2.1, 2004.6, 0.1)],
        n_sectors=3,
        seed=103,
    ),
    System(
        "SYN-4",
        "long-period sub-Neptune around a K dwarf (six contiguous sectors)",
        SyntheticStar(radius=0.7, mass=0.73, teff=4600),
        NoiseModel(white_ppm=300, red_ppm=40, rotation_ppm=800, rotation_period=30.0),
        [(35.6, 2.8, 2010.3, 0.4)],
        n_sectors=6,
        seed=104,
    ),
    System(
        "SYN-5",
        "eclipsing binary found at half its period (negative control)",
        SyntheticStar(radius=1.0, mass=1.0, teff=5800),
        NoiseModel(white_ppm=400, red_ppm=40, rotation_ppm=800, rotation_period=8.0),
        [],
        n_sectors=2,
        seed=105,
        eclipsing_binary=True,
    ),
]


def build(system: System) -> tuple[LightCurve, list[PublishedPlanet], StellarParams]:
    star = system.star
    stellar = StellarParams(
        radius=star.radius,
        radius_err=0.03 * star.radius,
        mass=star.mass,
        mass_err=0.05 * star.mass,
        teff=star.teff,
        teff_err=100.0,
        source="synthetic star (truth, with 3 % / 5 % radius / mass uncertainties)",
    )
    planets = [planet_from_physical(p, r, star, t0=t0, b=b) for p, r, t0, b in system.planets]
    lc = simulate_lightcurve(
        star, system.noise, planets, n_sectors=system.n_sectors, seed=system.seed
    )
    truth = [
        _truth(system, planet, radius, index)
        for index, (planet, (_, radius, _, _)) in enumerate(
            zip(planets, system.planets, strict=True)
        )
    ]
    if system.eclipsing_binary:
        # Two unequal eclipses per 5.6-day orbit: BLS sees a 2.8-day "planet".
        prim = TransitParams(2001.0, 5.6, 0.12, 11.0, 0.1, 0.45, 0.2)
        sec = TransitParams(2001.0 + 2.8, 5.6, 0.085, 11.0, 0.1, 0.45, 0.2)
        lc = lc.with_flux(lc.flux * transit_model(lc.time, prim) * transit_model(lc.time, sec))
        truth = []
    return lc, truth, stellar


def _truth(system: System, planet: SyntheticPlanet, radius: float, index: int) -> PublishedPlanet:
    """The injected planet, in the same container as archive reference values."""
    return PublishedPlanet(
        name=f"{system.name} {'bcdefg'[index]}",
        host=system.name,
        tic_id=None,
        period=planet.period,
        period_err=None,
        t0_btjd=planet.t0,
        depth_ppm=None,
        duration_hours=planet.to_params().t14 * 24,
        rp_rs=planet.rp_rs,
        rp_rs_err=None,
        rp_earth=radius,
        rp_earth_err=None,
        a_rs=planet.a_rs,
        impact=planet.b,
        stellar=StellarParams(radius=system.star.radius),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=Path("results/synthetic_benchmark"))
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--systems", nargs="*", default=None)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    workers = args.workers or default_n_workers()
    fit = FitConfig(n_workers=workers)
    if args.quick:
        fit = replace(fit, n_walkers=32, max_steps=3000, min_steps=1000)
    config = PipelineConfig()
    config = replace(config, search=replace(config.search, n_workers=workers), fit=fit)

    rows, systems = [], []
    for system in SYSTEMS:
        if args.systems and system.name not in args.systems:
            continue
        start = time.time()
        lc, truth, stellar = build(system)
        report = run_on_lightcurve(
            lc, args.out / system.name, stellar, config, name=f"{system.name} (synthetic)"
        )
        system_rows = [compare_planet(p, report) for p in truth]
        rows.extend(system_rows)
        systems.append(
            {
                "name": system.name,
                "description": system.description,
                "n_sectors": system.n_sectors,
                "noise_model": system.noise.__dict__,
                "star": system.star.__dict__,
                "eclipsing_binary": system.eclipsing_binary,
                "n_detections": report["search"]["n_detections"],
                "verdicts": [p["vetting"]["verdict"] for p in report["planets"]],
                "robust_cdpp_ppm": report["noise"]["robust_cdpp_ppm"],
                "runtime_s": time.time() - start,
            }
        )
        print(
            f"{system.name}: {report['search']['n_detections']} detections, verdicts "
            f"{systems[-1]['verdicts']} ({time.time() - start:.0f} s)",
            flush=True,
        )

    write_json(args.out / "benchmark.json", {"systems": systems, "comparison": rows})
    lines = [
        comparison_markdown(rows),
        "",
        "| system | description | sectors | detections | vetting verdicts |",
        "|---|---|---|---|---|",
    ]
    for s in systems:
        lines.append(
            f"| {s['name']} | {s['description']} | {s['n_sectors']} | "
            f"{s['n_detections']} | {'; '.join(s['verdicts']) or '–'} |"
        )
    (args.out / "benchmark.md").write_text("\n".join(lines) + "\n")
    if any(r["recovered"] for r in rows):
        plot_comparison(rows, args.out / "benchmark_errors.png")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
