"""End-to-end pipeline: light curve -> detrend -> search -> fit -> vet -> report.

Steps for one target:

1. Detrend the cleaned PDCSAP light curve (no mask) and run the iterative BLS
   search. If the catalogue density of the host is known it bounds the trial
   durations (see :class:`transit_hunter.search.SearchConfig`).
2. Detrend again with all detected transits masked, so that the trend under
   each transit is interpolated from out-of-transit data and depths are not
   biased low.
3. For each detected signal, fit a transit model by MCMC on data with the other
   signals' transits removed, then run the vetting tests.
4. Write every figure, a machine-readable ``report.json`` and a human-readable
   ``summary.md`` into one folder per target.
"""

from __future__ import annotations

import logging
import time as _time
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np

from . import __version__
from .catalog import StellarParams
from .data import CleaningConfig
from .detrend import DetrendConfig, detrend, ephemeris_mask, plot_detrending, sector_summary
from .fit import FitConfig, fit_transit, plot_corner, plot_fit
from .lightcurve import LightCurve
from .search import (
    SearchConfig,
    iterative_search,
    plot_folded,
    plot_periodogram,
    plot_search_summary,
)
from .utils import binned_rms, write_json
from .vet import VetConfig, plot_vetting, rotation_period, run_vetting

log = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    cleaning: CleaningConfig = field(default_factory=CleaningConfig)
    detrend: DetrendConfig = field(default_factory=DetrendConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    fit: FitConfig = field(default_factory=FitConfig)
    vet: VetConfig = field(default_factory=VetConfig)
    fit_signals: bool = True
    max_fits: int = 5
    mask_width_factor: float = 2.0
    use_stellar_density: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "cleaning": asdict(self.cleaning),
            "detrend": asdict(self.detrend),
            "search": asdict(self.search),
            "fit": asdict(self.fit),
            "vet": asdict(self.vet),
            "fit_signals": self.fit_signals,
            "max_fits": self.max_fits,
            "mask_width_factor": self.mask_width_factor,
            "use_stellar_density": self.use_stellar_density,
        }


def run_on_lightcurve(
    lc: LightCurve,
    outdir: str | Path,
    stellar: StellarParams | None = None,
    config: PipelineConfig | None = None,
    name: str = "target",
) -> dict[str, Any]:
    """Run the full pipeline on a cleaned light curve and write a report folder."""
    config = config or PipelineConfig()
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    started = _time.perf_counter()
    figures: dict[str, str] = {}

    search_cfg = config.search
    rho, _ = stellar.density_solar() if stellar is not None else (None, None)
    if config.use_stellar_density and rho:
        search_cfg = replace(search_cfg, stellar_density=float(rho))

    # 1. detrend + search
    log.info("%s: detrending %d points", name, len(lc))
    first = detrend(lc, config.detrend)
    figures["detrending"] = plot_detrending(first, outdir / "detrending.png", title=name).name
    log.info("%s: BLS search", name)
    result = iterative_search(first.flat, search_cfg, raw=lc, detrend_config=config.detrend)
    figures["search_summary"] = plot_search_summary(
        result, first.flat, outdir / "search_summary.png", title=f"{name}: iterative BLS"
    ).name
    for i, (sig, pg) in enumerate(zip(result.signals, result.periodograms, strict=False), 1):
        figures[f"periodogram_{i}"] = plot_periodogram(
            pg,
            sig,
            outdir / f"periodogram_{i}.png",
            title=f"{name}: BLS iteration {i}",
            sde_threshold=search_cfg.sde_threshold,
        ).name
        figures[f"fold_{i}"] = plot_folded(
            first.flat, sig, outdir / f"fold_{i}.png", title=f"{name}: signal {i}"
        ).name

    # 2. re-detrend with every detected transit masked; measure the rotation period
    # on the un-detrended light curve with the same transits left out.
    detections = result.detections
    planets: list[dict[str, Any]] = []
    mask = None
    if detections:
        mask = ephemeris_mask(lc.time, detections, width_factor=config.mask_width_factor)
        masked = detrend(lc, config.detrend, mask=mask)
        flat = masked.flat
    else:
        flat = first.flat
    rotation = rotation_period(lc, mask)

    # 3. fit + vet each candidate. A candidate's own same-period eclipses (signals
    # flagged ``secondary_of`` it) stay in its light curve so that the
    # secondary-eclipse test can see them; every other detection is masked.
    index_of = {id(s): i for i, s in enumerate(result.signals)}
    candidate_entries: dict[int, dict[str, Any]] = {}
    for n, sig in enumerate(result.candidates[: config.max_fits], 1):
        own = [s for s in detections if s.secondary_of == index_of[id(sig)]]
        others = [s for s in detections if s is not sig and not any(s is o for o in own)]
        keep = ~ephemeris_mask(flat.time, others, width_factor=config.mask_width_factor)
        planet_lc = flat.select(keep)
        entry: dict[str, Any] = {
            "role": "candidate",
            "signal": sig.as_dict(),
            "label": f"{name} candidate {n}",
            "same_period_signals": [s.iteration for s in own],
        }
        fit = None
        if config.fit_signals:
            try:
                log.info("%s: MCMC fit of signal %d (P = %.5f d)", name, n, sig.period)
                fit = fit_transit(
                    planet_lc, sig.period, sig.t0, sig.duration, sig.depth, stellar, config.fit
                )
                entry["fit"] = fit.as_dict()
                figures[f"fit_{n}"] = plot_fit(
                    fit, outdir / f"fit_{n}.png", title=f"{name}: candidate {n}"
                ).name
                figures[f"corner_{n}"] = plot_corner(
                    fit, outdir / f"corner_{n}.png", title=f"{name}: candidate {n}"
                ).name
            except (ValueError, RuntimeError) as exc:
                log.warning("fit of signal %d failed: %s", n, exc)
                entry["fit_error"] = str(exc)
        report = run_vetting(
            planet_lc,
            sig.period,
            sig.t0,
            sig.duration,
            fit,
            stellar,
            config.vet,
            depth=sig.depth,
            rotation=rotation,
        )
        entry["vetting"] = report.as_dict()
        figures[f"vetting_{n}"] = plot_vetting(
            planet_lc,
            sig.period,
            sig.t0,
            sig.duration,
            report,
            outdir / f"vetting_{n}.png",
            title=f"{name}: candidate {n}",
            fit=fit,
        ).name
        planets.append(entry)
        candidate_entries[index_of[id(sig)]] = entry

    # Same-period signals are the other eclipse of a candidate, not planets.
    for sig in detections:
        if sig.secondary_of is None:
            continue
        primary = candidate_entries.get(sig.secondary_of)
        test = None
        if primary is not None:
            test = next(t for t in primary["vetting"]["tests"] if t["name"] == "secondary")
        if test is not None and test["status"] == "fail":
            verdict = (
                f"secondary eclipse of an eclipsing binary (with signal "
                f"{sig.secondary_of + 1}, phase {sig.phase_offset:.2f})"
            )
        elif test is not None and test["status"] == "pass":
            verdict = (
                f"occultation of signal {sig.secondary_of + 1} (phase "
                f"{sig.phase_offset:.2f}), consistent with a planet"
            )
        else:
            verdict = (
                f"second eclipse of signal {sig.secondary_of + 1} at phase {sig.phase_offset:.2f}"
            )
        planets.append(
            {
                "role": "secondary",
                "signal": sig.as_dict(),
                "label": f"{name} signal {sig.iteration}",
                "secondary_of_signal": sig.secondary_of + 1,
                "vetting": {
                    "verdict": verdict,
                    "reasons": []
                    if test is None
                    else [
                        f"[{test['status']}] secondary (of signal {sig.secondary_of + 1}): "
                        f"{test['message']}"
                    ],
                    "tests": [],
                },
            }
        )

    cdpp = {
        f"{hours:g}h": binned_rms(first.flat.time, first.flat.flux, hours / 24) * 1e6
        for hours in (0.5, 1.0, 2.0)
    }
    report_json = {
        "target": {
            "name": name,
            "tic_id": lc.meta.get("tic_id"),
            "sectors": lc.sectors,
            "n_points": len(lc),
            "baseline_days": lc.baseline,
            "time_range_btjd": [float(lc.time.min()), float(lc.time.max())],
            "synthetic": bool(lc.meta.get("synthetic", False)),
        },
        "stellar": None if stellar is None else stellar.as_dict(),
        "noise": {"robust_cdpp_ppm": cdpp, "per_sector": sector_summary(first.flat)},
        "rotation": rotation,
        "search": {
            "baseline_days": result.baseline,
            "n_points": result.n_points,
            "stellar_density_used": search_cfg.stellar_density,
            "signals": [s.as_dict() for s in result.signals],
            "n_detections": len(detections),
            "n_candidates": len(result.candidates),
        },
        "planets": planets,
        "config": replace_config_for_report(config, search_cfg),
        "figures": figures,
        "software": {"transit_hunter": __version__},
        "data_provenance": {
            k: lc.meta.get(k)
            for k in ("cache_file", "created_utc", "versions", "sector_stats", "cleaning")
        },
        "runtime_s": _time.perf_counter() - started,
    }
    write_json(outdir / "report.json", report_json)
    (outdir / "summary.md").write_text(render_summary(report_json))
    log.info("%s: report written to %s", name, outdir)
    return report_json


def replace_config_for_report(config: PipelineConfig, search_cfg: SearchConfig) -> dict[str, Any]:
    out = config.as_dict()
    out["search"] = asdict(search_cfg)
    return out


def _fmt(entry: dict[str, float] | None, digits: int = 3) -> str:
    if not entry or entry.get("median") is None or not np.isfinite(entry["median"]):
        return "–"
    return f"{entry['median']:.{digits}g} +{entry['err_hi']:.2g} / −{entry['err_lo']:.2g}"


def _mcmc_line(fit: dict[str, Any]) -> str:
    taus = [t for t in fit["autocorr_time"].values() if t == t]
    tau = max(taus) if taus else float("nan")
    convergence = (
        "converged (longer than 50 autocorrelation times, estimate stable to 1 %)"
        if fit["converged"]
        else "not converged (that needs more than 50 autocorrelation times); treat the "
        "posterior tails with caution"
    )
    return (
        f"MCMC: {fit['n_steps']} steps, {fit['n_steps'] / tau:.0f} times the longest "
        f"autocorrelation time ({tau:.0f} steps); {fit['n_samples']} samples after burn-in "
        f"and thinning, acceptance {fit['acceptance_fraction']:.2f}; {convergence}."
    )


def render_summary(report: dict[str, Any]) -> str:
    """Markdown summary of a pipeline report."""
    t = report["target"]
    lines = [f"# {t['name']}", ""]
    if t.get("synthetic"):
        lines += ["> **Synthetic light curve** – not a real star.", ""]
    lines += [
        f"* Sectors: {', '.join(map(str, t['sectors'])) or 'n/a'}; {t['n_points']} points over "
        f"{t['baseline_days']:.1f} days",
    ]
    st = report.get("stellar")
    if st:

        def num(value: float | None, fmt: str) -> str:
            return "n/a" if value is None or value != value else format(value, fmt)

        lines.append(
            f"* Host star ({st['source']}): R* = {num(st.get('radius'), '.3g')} R☉, "
            f"Teff = {num(st.get('teff'), '.0f')} K, "
            f"ρ* = {num(st.get('density_derived'), '.3g')} ρ☉"
        )
    cdpp = report["noise"]["robust_cdpp_ppm"]
    lines.append(
        "* Scatter of the flattened light curve (robust, binned): "
        + ", ".join(f"{k}: {v:.0f} ppm" for k, v in cdpp.items() if v == v)
    )
    rot = report.get("rotation") or {}
    if rot.get("period") == rot.get("period") and rot.get("period") is not None:
        lines.append(
            f"* Strongest periodicity of the un-detrended light curve (Lomb–Scargle, transits "
            f"masked): {rot['period']:.2f} d, semi-amplitude {rot['amplitude_ppm']:.0f} ppm, "
            f"power {rot['power']:.2f}"
        )
    lines += [
        "",
        "## Search",
        "",
        "| # | period (d) | T0 (BTJD) | duration (h) | depth (ppm) | S/N | SDE | status |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in report["search"]["signals"]:
        if s["detected"] and s.get("secondary_of") is not None:
            status = f"same period as #{s['secondary_of'] + 1} (phase {s['phase_offset']:.2f})"
        elif s["detected"]:
            status = "detected"
        elif s["harmonic_of"] is not None:
            status = f"harmonic of #{s['harmonic_of'] + 1}"
        else:
            status = "below threshold"
        lines.append(
            f"| {s['iteration']} | {s['period']:.5f} | {s['t0']:.4f} | {s['duration'] * 24:.2f} | "
            f"{s['depth'] * 1e6:.0f} | {s['snr']:.1f} | {s['sde']:.1f} | {status} |"
        )
    skipped = [
        (s["iteration"], peak)
        for s in report["search"]["signals"]
        for peak in s.get("skipped_peaks", [])
    ]
    if skipped:
        lines += ["", "Stronger peaks skipped in favour of the signals above:", ""]
        lines += [
            f"* iteration {it}: P = {peak['period']:.5f} d, SDE {peak['sde']:.1f}: {peak['reason']}"
            for it, peak in skipped
        ]
    n_candidate = 0
    for planet in report["planets"]:
        if planet.get("role") == "secondary":
            lines += [
                "",
                f"## Signal {planet['signal']['iteration']} (not a planet)",
                "",
                f"**{planet['vetting']['verdict']}**",
                "",
            ]
            lines += [f"* {reason}" for reason in planet["vetting"]["reasons"]]
            continue
        n_candidate += 1
        lines += ["", f"## Candidate {n_candidate}", ""]
        fit = planet.get("fit")
        if fit:
            post = fit["posterior"]
            lines += [
                "| parameter | posterior median and 68 % interval |",
                "|---|---|",
                f"| period (d) | {_fmt(post['period'], 8)} |",
                f"| T0 (BTJD) | {_fmt(post['t0'], 9)} |",
                f"| Rp/R* | {_fmt(post['rp_rs'])} |",
                f"| a/R* | {_fmt(post['a_rs'])} |",
                f"| b | {_fmt(post['b'])} |",
                f"| T14 (h) | {_fmt(post['t14_hours'])} |",
                f"| depth k² (ppm) | {_fmt(post['depth_ppm'])} |",
                f"| ρ* (ρ☉) | {_fmt(post['rho_star_solar'])} |",
                f"| Rp (R⊕) | {_fmt(post.get('rp_earth'))} |",
                "",
                _mcmc_line(fit),
            ]
        vet = planet["vetting"]
        lines += ["", f"**Vetting verdict: {vet['verdict']}**", ""]
        lines += [f"* {reason}" for reason in vet["reasons"]]
    lines += ["", "## Figures", ""]
    lines += [f"* [{key}]({name})" for key, name in report["figures"].items()]
    return "\n".join(lines) + "\n"
