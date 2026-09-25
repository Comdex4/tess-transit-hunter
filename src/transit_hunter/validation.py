"""Validation of the pipeline against confirmed planets (NASA Exoplanet Archive).

The comparison is deliberately simple and transparent:

* period: MCMC posterior median vs ``pl_orbper``;
* depth: the geometric depth ``(Rp/R*)^2`` from the fit vs ``pl_ratror^2``
  (the one depth definition shared by the fit and the archive; the archive's
  ``pl_trandep`` is used only if no radius ratio is listed, and the table says so);
* planet radius: ``k * R*`` with the TIC stellar radius vs ``pl_rade`` (the
  radius-ratio column isolates the part of any difference due to the light
  curve rather than the adopted stellar radius).

Percent errors are ``100 * (recovered - published) / published``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .catalog import PublishedPlanet
from .plotting import AQUA, BLUE, INK, INK_SECONDARY, ORANGE, new_figure, save_figure, style


@dataclass(frozen=True)
class ValidationTarget:
    """A host star whose transiting planets are used for validation.

    Planets are matched to the star by TIC ID: the archive's host names do not
    always follow the common name (it lists pi Men as HD 39091 and HD 21749 as
    GJ 143).
    """

    host: str  # common name, used for display and folder names
    tic_id: int  # TESS Input Catalog ID
    note: str  # why it is in the sample (qualitative; numbers come from the archive)


#: Confirmed TESS planets spanning ultra-short to long periods and giant to
#: Earth-sized radii, around FGK and M dwarfs, including two multi-planet systems.
DEFAULT_TARGETS = (
    ValidationTarget("WASP-18", 100100827, "hot Jupiter on a sub-day orbit (large, short period)"),
    ValidationTarget("pi Men", 261136679, "small planet around a very bright G dwarf"),
    ValidationTarget("TOI-270", 259377017, "compact M-dwarf multi-planet system near resonance"),
    ValidationTarget("L 98-59", 307210830, "M-dwarf system with Earth-sized and smaller planets"),
    ValidationTarget("HD 21749", 279741379, "long-period sub-Neptune (plus an inner small planet)"),
)


def pct_error(recovered: float | None, published: float | None) -> float | None:
    if recovered is None or published is None or published == 0:
        return None
    if not (math.isfinite(recovered) and math.isfinite(published)):
        return None
    return 100.0 * (recovered - published) / published


def _posterior(fit: dict[str, Any] | None, name: str) -> tuple[float | None, float | None]:
    if not fit:
        return None, None
    entry = fit["posterior"].get(name)
    if not entry or entry.get("median") is None:
        return None, None
    return entry["median"], 0.5 * (entry["err_lo"] + entry["err_hi"])


def compare_planet(
    published: PublishedPlanet, report: dict[str, Any], period_tolerance: float = 0.01
) -> dict[str, Any]:
    """Match one published planet to the pipeline report of its host star."""
    row: dict[str, Any] = {
        "planet": published.name,
        "host": published.host,
        "tic_id": published.tic_id,
        "period_pub": published.period,
        "period_pub_err": published.period_err,
        "rp_pub": published.rp_earth,
        "rp_pub_err": published.rp_earth_err,
        "rp_rs_pub": published.rp_rs,
        "recovered": False,
    }
    if published.rp_rs is not None:
        row["depth_pub_ppm"] = published.rp_rs**2 * 1e6
        row["depth_pub_kind"] = "(Rp/R*)^2"
    else:
        row["depth_pub_ppm"] = published.depth_ppm
        row["depth_pub_kind"] = "transit depth" if published.depth_ppm is not None else None
    if published.period is None:
        return row

    match = None
    for planet in report.get("planets", []):
        if planet.get("role", "candidate") != "candidate":
            continue  # the other eclipse of a candidate, not a planet
        period = planet["signal"]["period"]
        if abs(period - published.period) < period_tolerance * published.period:
            match = planet
            break
    if match is None:
        # Detected but not fitted, or seen only below threshold: report the closest signal.
        for sig in report.get("search", {}).get("signals", []):
            if abs(sig["period"] - published.period) < period_tolerance * published.period:
                row.update(
                    found_below_threshold=not sig["detected"],
                    sde=sig["sde"],
                    snr=sig["snr"],
                    period_bls=sig["period"],
                )
        return row

    sig = match["signal"]
    fit = match.get("fit")
    period, period_err = _posterior(fit, "period")
    k, k_err = _posterior(fit, "rp_rs")
    depth, depth_err = _posterior(fit, "depth_ppm")
    rp, rp_err = _posterior(fit, "rp_earth")
    if period is None:  # no MCMC fit: fall back to BLS
        period, depth = sig["period"], sig["depth"] * 1e6
    row.update(
        recovered=True,
        period_bls=sig["period"],
        sde=sig["sde"],
        snr=sig["snr"],
        period_rec=period,
        period_rec_err=period_err,
        rp_rs_rec=k,
        rp_rs_rec_err=k_err,
        depth_rec_ppm=depth,
        depth_rec_err=depth_err,
        rp_rec=rp,
        rp_rec_err=rp_err,
        period_pct=pct_error(period, published.period),
        depth_pct=pct_error(depth, row["depth_pub_ppm"]),
        rp_rs_pct=pct_error(k, published.rp_rs),
        rp_pct=pct_error(rp, published.rp_earth),
        verdict=match.get("vetting", {}).get("verdict"),
        converged=None if not fit else fit.get("converged"),
    )
    return row


def detection_rows(
    report: dict[str, Any], published: list[PublishedPlanet], period_tolerance: float = 0.01
) -> list[dict[str, Any]]:
    """Every detection in a pipeline report, the published planet it matches, and its verdict.

    Unlike :func:`compare_planet`, which starts from the published planets, this starts
    from the detections, so signals that match no known planet are listed too.
    """
    rows = []
    for planet in report.get("planets", []):
        sig = planet["signal"]
        role = planet.get("role", "candidate")
        match = None
        if role == "candidate":
            match = next(
                (
                    p.name
                    for p in published
                    if p.period and abs(sig["period"] - p.period) < period_tolerance * p.period
                ),
                None,
            )
        vetting = planet.get("vetting") or {}
        tests = vetting.get("tests", []) if role == "candidate" else []
        rows.append(
            {
                "iteration": sig["iteration"],
                "period": sig["period"],
                "snr": sig["snr"],
                "role": role,
                "matches": match,
                "verdict": vetting.get("verdict") or planet.get("label"),
                "failed": [t["name"] for t in tests if t["status"] == "fail"],
                "warnings": [t["name"] for t in tests if t["status"] == "warn"],
            }
        )
    return rows


def detections_markdown(hosts: list[dict[str, Any]]) -> str:
    """Table of every detection per host (``hosts[i]["detections"]`` from detection_rows)."""
    lines = [
        "| host | sectors | signal | P (d) | S/N | published planet | vetting verdict | "
        "failed tests / warnings |",
        "|" + "---|" * 8,
    ]
    for host in hosts:
        for d in host["detections"]:
            flags = [
                f"{label}: {', '.join(d[key])}"
                for key, label in (("failed", "failed"), ("warnings", "warnings"))
                if d[key]
            ]
            lines.append(
                f"| {host['host']} | {len(host['sectors'])} | {d['iteration']} | "
                f"{d['period']:.5f} | {d['snr']:.1f} | {d['matches'] or '–'} | {d['verdict']} | "
                f"{'; '.join(flags) or '–'} |"
            )
    return "\n".join(lines) + "\n"


def _num(value: float | None, fmt: str) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "–"
    return format(value, fmt)


def _pm(value: float | None, err: float | None, fmt: str) -> str:
    if value is None:
        return "–"
    if err is None:
        return _num(value, fmt)
    return f"{_num(value, fmt)} ± {_num(err, '.2g')}"


def comparison_markdown(rows: list[dict[str, Any]]) -> str:
    """Recovered-vs-published table (percent errors in parentheses)."""
    head = (
        "| planet | P published (d) | P recovered (d) | ΔP | depth published (ppm) | "
        "depth recovered (ppm) | Δdepth | Rp published (R⊕) | Rp recovered (R⊕) | ΔRp |"
    )
    lines = [head, "|" + "---|" * 10]
    for r in rows:
        if not r["recovered"]:
            note = "not recovered"
            if r.get("found_below_threshold"):
                note += f" (peak below threshold: S/N {r['snr']:.1f}, SDE {r['sde']:.1f})"
            lines.append(
                f"| {r['planet']} | {_num(r['period_pub'], '.6f')} | {note} | | "
                f"{_num(r.get('depth_pub_ppm'), '.0f')} | | | {_num(r['rp_pub'], '.2f')} | | |"
            )
            continue
        lines.append(
            f"| {r['planet']} | {_num(r['period_pub'], '.6f')} | "
            f"{_pm(r['period_rec'], r.get('period_rec_err'), '.6f')} | "
            f"{_num(r['period_pct'], '+.4f')}% | "
            f"{_num(r.get('depth_pub_ppm'), '.0f')} | "
            f"{_pm(r['depth_rec_ppm'], r.get('depth_rec_err'), '.0f')} | "
            f"{_num(r['depth_pct'], '+.1f')}% | "
            f"{_pm(r['rp_pub'], r.get('rp_pub_err'), '.2f')} | "
            f"{_pm(r['rp_rec'], r.get('rp_rec_err'), '.2f')} | "
            f"{_num(r['rp_pct'], '+.1f')}% |"
        )
    kinds = {r.get("depth_pub_kind") for r in rows if r.get("depth_pub_kind")}
    notes = [
        "",
        "Depth is the geometric depth (Rp/R*)² unless noted; Δ = "
        "100 × (recovered − published) / published.",
    ]
    if "transit depth" in kinds:
        notes.append(
            "Some published depths are archive `pl_trandep` values (no radius ratio "
            "listed); those comparisons mix depth definitions."
        )
    return "\n".join(lines + notes) + "\n"


def plot_comparison(rows: list[dict[str, Any]], path: str | Path) -> Path:
    """Percent error of period, depth, and radius for each recovered planet.

    Error bars are the recovered values' 68 % intervals, in percent of the
    published value (the published uncertainties are not included).
    """
    done = [r for r in rows if r["recovered"]]
    names = [r["planet"] for r in done]
    y = np.arange(len(done))
    quantities = [
        ("depth_pct", "depth_rec_err", "depth_pub_ppm", "depth (Rp/R*)²", BLUE),
        ("rp_pct", "rp_rec_err", "rp_pub", "planet radius", ORANGE),
        ("period_pct", "period_rec_err", "period_pub", "period", AQUA),
    ]

    def value(row: dict[str, Any], key: str) -> float:
        return np.nan if row.get(key) is None else float(row[key])

    with style():
        fig, axes = new_figure(1, 1, figsize=(8, 0.5 * max(len(done), 2) + 1.6))
        ax = axes[0, 0]
        for offset, (key, err_key, pub_key, label, color) in zip(
            (-0.2, 0.0, 0.2), quantities, strict=True
        ):
            values = [value(r, key) for r in done]
            errors = [100 * value(r, err_key) / value(r, pub_key) for r in done]
            ax.errorbar(
                values,
                y + offset,
                xerr=np.abs(errors),
                fmt="o",
                ms=7,
                color=color,
                mec="white",
                mew=1.0,
                elinewidth=1.6,
                capsize=0,
                label=label,
            )
        ax.axvline(0.0, color=INK, lw=0.9)
        ax.set_yticks(y, names)
        ax.invert_yaxis()
        ax.set_xlabel("recovered − published (% of published)")
        ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=3, borderaxespad=0.1)
        ax.tick_params(axis="y", labelcolor=INK_SECONDARY)
        return save_figure(fig, path)
