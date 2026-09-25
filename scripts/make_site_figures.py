#!/usr/bin/env python
"""Draw the explanatory figures of the documentation site (docs/assets/site/).

Each figure either runs the package's own code on simulated light curves (outlier
clipping, detrending, folding, transit shapes) or re-plots numbers already saved in
results/ (threshold scaling, recovery curves). Nothing here is typed by hand.

    python scripts/make_site_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from transit_hunter import plotting as P
from transit_hunter.data import find_outliers
from transit_hunter.detrend import DetrendConfig, detrend, ephemeris_mask
from transit_hunter.models import TransitParams, a_rs_from_mass_radius, t14, transit_model
from transit_hunter.synthetic import (
    NoiseModel,
    SyntheticStar,
    planet_from_physical,
    simulate_lightcurve,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "site"
RESULTS = ROOT / "results"
SEQ = P.SEQUENTIAL_BLUE


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    P.save_figure(fig, OUT / name)
    print("wrote", (OUT / name).relative_to(ROOT))


def title(ax, text: str) -> None:
    ax.set_title(text, loc="left", fontsize=12, fontweight="bold", color=P.INK)


# --------------------------------------------------------------------------- 1 clipping
def fig_clipping() -> None:
    star = SyntheticStar(1.0, 1.0, 5770)
    planet = planet_from_physical(3.0, 11.0, star, t0=2001.5, b=0.2)
    noise = NoiseModel(white_ppm=900, red_ppm=0, rotation_ppm=300, outlier_rate=0.004)
    lc = simulate_lightcurve(star, noise, [planet], n_sectors=1, seed=4)
    sym = find_outliers(lc.time, lc.flux, sigma_upper=4.0, sigma_lower=4.0)
    asym = find_outliers(lc.time, lc.flux, sigma_upper=4.0)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    sel = (lc.time > 2000.9) & (lc.time < 2002.1)
    for ax, flags, label in (
        (axes[0], sym, "symmetric clip"),
        (axes[1], asym, "upper-only clip (default)"),
    ):
        t, f, o = lc.time[sel], (lc.flux[sel] - 1) * 1e3, flags[sel]
        ax.plot(t[~o], f[~o], ".", ms=2.5, color=P.INK_MUTED, label="kept")
        ax.plot(t[o], f[o], "o", ms=5, mfc="none", mec=P.ORANGE, mew=1.3, label="removed")
        intr = sel & (np.abs(((lc.time - planet.t0 + 1.5) % 3.0) - 1.5) < 0.06)
        lost = int((flags & intr).sum())
        title(ax, f"{label}: {lost} of {int(intr.sum())} in-transit points lost")
        ax.set_xlabel("time (BTJD days)")
        ax.grid(True, lw=0.5)
    axes[0].set_ylabel("flux − 1 (ppt)")
    axes[1].legend(frameon=False, loc="upper right")
    fig.tight_layout()
    save(fig, "clipping.png")


# --------------------------------------------------------------------------- 2 detrending
def fig_detrend_depth() -> None:
    star = SyntheticStar(1.0, 1.0, 5770)
    windows = np.array([0.25, 0.35, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0])
    period = 7.3
    planet = planet_from_physical(period, 2.5, star, t0=2002.0, b=0.2)
    dur = t14(period, planet.a_rs, planet.rp_rs, planet.b)
    noise = NoiseModel(white_ppm=60, red_ppm=0, rotation_ppm=800, rotation_period=5.0)
    lc = simulate_lightcurve(star, noise, [planet], n_sectors=2, seed=7)
    model = transit_model(lc.time, planet.to_params())
    intr = model < 1 - 1e-7
    true_def = np.mean(1 - model[intr])
    mask = ephemeris_mask(lc.time, [(period, planet.t0, dur)], width_factor=2.0)
    kept = {"unmasked": [], "masked": []}
    for w in windows:
        cfg = DetrendConfig(window_length=float(w))
        for key, m in (("unmasked", None), ("masked", mask)):
            res = detrend(lc, cfg, mask=m)
            it = np.interp(res.flat.time, lc.time, intr.astype(float)) > 0.5
            kept[key].append(np.mean(1 - res.flat.flux[it]) / true_def)
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    x = windows
    ax.plot(
        x,
        100 * np.array(kept["masked"]),
        "-o",
        color=P.BLUE,
        lw=2,
        ms=7,
        mec=P.SURFACE,
        mew=2,
        label="transits masked (fit and vetting)",
    )
    ax.plot(
        x,
        100 * np.array(kept["unmasked"]),
        "-o",
        color=P.ORANGE,
        lw=2,
        ms=7,
        mec=P.SURFACE,
        mew=2,
        label="no mask (first search pass)",
    )
    ax.axvline(0.75, color=P.AXIS, ls="--", lw=1)
    ax.text(0.78, 62, "default\n0.75 d window", fontsize=9.5, color=P.INK_SECONDARY)
    ax.set_xscale("log")
    ax.set_ylim(55, 105)
    ax.set_xticks(windows)
    ax.set_xticklabels([f"{w:g}" for w in windows])
    ax.minorticks_off()
    ax.set_xlabel("biweight window length (days)")
    ax.set_ylabel("transit depth kept (%)")
    ax.grid(True, lw=0.5)
    ax.legend(frameon=False, loc="lower left")
    title(ax, f"How much of a {dur * 24:.1f}-hour transit survives the biweight filter")
    fig.tight_layout()
    save(fig, "detrend_depth.png")


# --------------------------------------------------------------------------- 3 folding
def fig_folding() -> None:
    star = SyntheticStar(0.8, 0.8, 5100)
    planet = planet_from_physical(4.2, 2.2, star, t0=2001.3, b=0.3)
    noise = NoiseModel(white_ppm=900, red_ppm=0, rotation_ppm=0)
    lc = simulate_lightcurve(star, noise, [planet], n_sectors=2, seed=11)
    trials = [
        (planet.period, "true period P"),
        (planet.period * 1.004, "P × 1.004 (smeared)"),
        (planet.period / 2, "P / 2 (diluted)"),
        (planet.period * 2, "2P (half the transits)"),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.4), sharey=True)
    for ax, (per, label) in zip(axes, trials, strict=True):
        ph = ((lc.time - planet.t0) / per + 0.5) % 1 - 0.5
        hrs = ph * per * 24
        sel = np.abs(hrs) < 8
        ax.plot(hrs[sel], (lc.flux[sel] - 1) * 1e6, ".", ms=1.5, color=P.AXIS)
        edges = np.linspace(-8, 8, 49)
        idx = np.digitize(hrs[sel], edges)
        f = (lc.flux[sel] - 1) * 1e6
        b = [np.mean(f[idx == i]) for i in range(1, len(edges))]
        ax.plot(0.5 * (edges[1:] + edges[:-1]), b, "o", ms=4, color=P.BLUE)
        ax.set_ylim(-1600, 900)
        ax.set_xlabel("hours from trial mid-transit")
        ax.grid(True, lw=0.5)
        ax.set_title(label, loc="left", fontsize=10.5, color=P.INK)
    axes[0].set_ylabel("flux − 1 (ppm)")
    fig.suptitle(
        "Folding one light curve at four trial periods (2.2 R⊕ planet, 4.2 d)",
        x=0.01,
        ha="left",
        fontsize=12,
        fontweight="bold",
        color=P.INK,
    )
    fig.tight_layout()
    save(fig, "folding.png")


# --------------------------------------------------------------------------- 4 thresholds
def fig_threshold() -> None:
    data = json.loads((RESULTS / "performance/search_scaling.json").read_text())
    rows = data["rows"]
    n = np.logspace(4, 9, 200)
    alpha = 0.01
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    ax.plot(
        n,
        np.sqrt(2 * np.log(n / alpha)),
        color=P.BLUE,
        lw=2,
        label=r"trial-corrected 1 % level  $\sqrt{2\ln(N/\alpha)}$",
    )
    ax.axhline(7, color=P.ORANGE, lw=2, label="floor: S/N = 7")
    for r in rows:
        ax.plot(
            r["n_effective_trials"],
            r["top_peak_snr"],
            "o",
            ms=8,
            color=P.INK_SECONDARY,
            mec=P.SURFACE,
            mew=2,
        )
    ax.plot([], [], "o", color=P.INK_SECONDARY, label="strongest peak in pure noise (measured)")
    ax.set_xscale("log")
    ax.set_ylim(4, 8)
    ax.set_xlabel("effective number of independent trials N")
    ax.set_ylabel("S/N")
    ax.grid(True, lw=0.5)
    ax.legend(frameon=False, loc="lower right", fontsize=9.5)
    title(ax, "Searching longer means more chances for noise to look like a planet")
    fig.tight_layout()
    save(fig, "threshold.png")


# --------------------------------------------------------------------------- 5 shapes
def fig_impact_shapes() -> None:
    period, k = 5.0, 0.1
    a_rs = a_rs_from_mass_radius(period, 1.0, 1.0)
    time = np.linspace(-0.15, 0.15, 3000)
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    for b, c in zip((0.0, 0.5, 0.8, 0.95), (SEQ[12], SEQ[9], SEQ[6], SEQ[3]), strict=True):
        tp = TransitParams(0.0, period, k, a_rs, b, 0.4, 0.2)
        f = transit_model(time, tp)
        ax.plot(time * 24, (f - 1) * 1e6, color=c, lw=2, label=f"b = {b:g}")
    ax.set_xlabel("hours from mid-transit")
    ax.set_ylabel("flux − 1 (ppm)")
    ax.grid(True, lw=0.5)
    ax.legend(frameon=False, loc="lower right", title="impact parameter")
    title(ax, "Same planet (Rp/R* = 0.1), different impact parameters")
    fig.tight_layout()
    save(fig, "impact_shapes.png")


# --------------------------------------------------------------------------- 6 recovery
def fig_recovery_curves() -> None:
    d = json.loads((RESULTS / "injection_synthetic/completeness.json").read_text())
    pe, re_ = np.array(d["period_edges"]), np.array(d["radius_edges"])
    rec, tot = np.array(d["recovered"]), np.array(d["total"])  # [radius, period]
    rc = np.sqrt(re_[1:] * re_[:-1])
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    shades = (SEQ[3], SEQ[6], SEQ[9], SEQ[12])
    for j, c in zip(range(0, rec.shape[1], 2), shades, strict=True):
        frac = rec[:, j : j + 2].sum(axis=1) / tot[:, j : j + 2].sum(axis=1)
        ax.plot(
            rc,
            100 * frac,
            "-o",
            color=c,
            lw=2,
            ms=7,
            mec=P.SURFACE,
            mew=1.5,
            label=f"{pe[j]:.2g}–{pe[j + 2]:.2g} d",
        )
    ax.set_xscale("log")
    ax.set_xticks([0.8, 1, 1.5, 2, 3, 5, 7])
    ax.set_xticklabels(["0.8", "1", "1.5", "2", "3", "5", "7"])
    ax.set_xlabel("planet radius (R⊕)")
    ax.set_ylabel("recovered (%)")
    ax.grid(True, lw=0.5)
    ax.legend(frameon=False, title="orbital period", loc="lower right")
    title(ax, "Recovery rate by size: shorter periods reach smaller planets")
    fig.tight_layout()
    save(fig, "recovery_curves.png")


def main() -> None:
    plt.switch_backend("Agg")
    with P.style():
        fig_clipping()
        fig_detrend_depth()
        fig_folding()
        fig_threshold()
        fig_impact_shapes()
        fig_recovery_curves()


if __name__ == "__main__":
    main()
