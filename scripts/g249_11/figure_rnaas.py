"""The figure of the G 249-11 research note (RNAAS): the transit in every epoch.

The layout of Figure 1 of the longer note (``figure1.py``), drawn from the light curves
used with the published tools (``tess_data.py``: SPOC 2-minute PDCSAP; QLP detrended
flux with QUALITY = 0) and sized for a journal page. (a)-(c): the data folded at the
fitted ephemeris, one panel per epoch, in 15-minute bins, with the maximum-posterior
transit model of the fit to the 2-minute data (``s19-59-60/report.json``); (d): the
individual 2-minute transits in 30-minute bins, each with the same model.

Usage, from the repository root::

    python scripts/g249_11/figure_rnaas.py

Writes ``papers/rnaas_g249-11/figure1.pdf`` (for the journal) and ``figure1.png``.
"""

import json
import math
from pathlib import Path

import batman
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import tess_data

matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "papers" / "rnaas_g249-11"
fit = json.loads((ROOT / "results" / "g249-11" / "s19-59-60" / "report.json").read_text())
fit = fit["planets"][0]["fit"]
p = fit["max_posterior_sample"]
P, T0 = p["period"], p["t0"]
DATA, BIN, MODEL = "#b8b8b8", "#1f3b73", "#d95f02"


def model_ppm(hours):
    """The maximum-posterior batman model, 2-minute exposures, in ppm."""
    params = batman.TransitParams()
    params.t0, params.per, params.rp = 0.0, P, p["rp_rs"]
    params.a = math.exp(p["ln_a_rs"])
    params.inc = math.degrees(math.acos(min(p["b"] / params.a, 1.0)))
    params.ecc, params.w, params.limb_dark = 0.0, 90.0, "quadratic"
    q1, q2 = p["q1"], p["q2"]
    params.u = [2 * math.sqrt(q1) * q2, math.sqrt(q1) * (1 - 2 * q2)]  # Kipping (2013)
    model = batman.TransitModel(
        params, hours / 24, supersample_factor=fit["supersample"], exp_time=120 / 86400
    )
    return (model.light_curve(params) - 1) * 1e6


def phase_hours(time):
    return (((time - T0) / P + 0.5) % 1.0 - 0.5) * P * 24


def binned(x, y, width, lo=-3.0, hi=3.0):
    edges = np.arange(lo, hi + 1e-9, width)
    idx = np.digitize(x, edges) - 1
    centers, means, errs = [], [], []
    for k in range(len(edges) - 1):
        sel = idx == k
        if sel.sum() >= 3:
            centers.append(0.5 * (edges[k] + edges[k + 1]))
            means.append(np.mean(y[sel]))
            errs.append(np.std(y[sel]) / np.sqrt(sel.sum()))
    return np.array(centers), np.array(means), np.array(errs)


def main():
    PAPER.mkdir(parents=True, exist_ok=True)
    data = tess_data.load(tess_data.SPOC_SECTORS + tess_data.QLP_SECTORS)
    hours = np.linspace(-3, 3, 721)
    curve = model_ppm(hours)
    plt.rcParams.update({"font.size": 8, "axes.labelsize": 8})
    fig = plt.figure(figsize=(7.1, 5.4))
    gs = fig.add_gridspec(3, 2, width_ratios=[1.5, 1], hspace=0.1, wspace=0.12)
    epochs = [
        ("(a) Sector 19, 2019: SPOC 2-min", (19,)),
        ("(b) Sectors 59-60, 2022-23: SPOC 2-min", (59, 60)),
        ("(c) Sectors 73 and 86, 2023-24: QLP 200-s", (73, 86)),
    ]
    axes = []
    for row, (label, sectors) in enumerate(epochs):
        ax = fig.add_subplot(gs[row, 0], sharex=axes[0] if axes else None)
        axes.append(ax)
        t, _, flux, _ = tess_data.joined({s: data[s] for s in sectors})
        x, y = phase_hours(t), (flux - 1) * 1e6
        m = np.abs(x) < 3
        ax.plot(x[m], y[m], ".", ms=1.2, color=DATA, zorder=1, rasterized=True)
        c, mu, e = binned(x[m], y[m], 0.25)
        level = np.median(mu[np.abs(c) > 1])
        ax.errorbar(c, mu - level, e, fmt="o", ms=2.5, color=BIN, lw=0.8, zorder=3)
        ax.plot(hours, curve, color=MODEL, lw=1.2, zorder=4)
        ax.set_ylim(-6500, 4500)
        ax.text(0.01, 0.95, label, transform=ax.transAxes, va="top")
        ax.set_ylabel("relative flux (ppm)")
        if row < 2:
            ax.tick_params(labelbottom=False)
    axes[-1].set_xlabel("hours from mid-transit")
    axes[0].set_xlim(-3, 3)

    ax = fig.add_subplot(gs[:, 1])
    step = 9000.0
    transits = []
    for s in tess_data.SPOC_SECTORS:
        lc = data[s]
        for n in np.unique(np.round((lc.time - T0) / P)):
            x = (lc.time - T0 - n * P) * 24
            m = np.abs(x) < 3
            if np.sum(np.abs(x) < 0.4) >= 5 and m.sum() > 60:
                transits.append((s, x[m], (lc.flux[m] - 1) * 1e6))
    for k, (s, x, y) in enumerate(transits):
        off = -k * step
        c, mu, e = binned(x, y, 0.5)
        level = np.median(mu[np.abs(c) > 1])
        ax.errorbar(c, mu - level + off, e, fmt="o", ms=2.2, color=BIN, lw=0.7)
        ax.plot(hours, curve + off, color=MODEL, lw=0.9)
        ax.text(3.15, off, f"S{s}", fontsize=6.5, va="center", color="#555555")
    ax.set_xlim(-3, 3.9)
    ax.set_ylim(-(len(transits) - 1) * step - 8000, 4500)
    ax.set_yticks([])
    ax.set_xlabel("hours from mid-transit")
    ax.set_title(
        f"(d) The {len(transits)} 2-minute transits\n(30-min bins, offset by 9,000 ppm)",
        fontsize=8,
        loc="left",
    )
    for a in [*axes, ax]:
        for side in ("top", "right"):
            a.spines[side].set_visible(False)
    for ext in ("pdf", "png"):
        fig.savefig(PAPER / f"figure1.{ext}", dpi=200, bbox_inches="tight")
    print(f"model depth {-curve.min():.0f} ppm; {len(transits)} individual transits")


if __name__ == "__main__":
    main()
