"""Figure 2 of the G 249-11 note, drawn from the output of figure2_compute.py.

(a) First search pass: SDE against trial period, the candidate's period and its aliases marked.
(b) Second pass, after re-detrending with the candidate's transits masked.
Trials whose best box holds fewer than two transits with data are left out, as in the pipeline.

Usage, from the repository root (after figure2_compute.py)::

    python scripts/g249_11/figure2_plot.py

Writes ``results/g249-11/figure2.png``.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parents[2] / "results" / "g249-11"
P = 5.307419
d = np.load(OUT / "figure2_passes.npz")
meta = json.loads((OUT / "figure2_passes.json").read_text())
threshold = meta["sde_threshold"]

INK, ALIAS, GRID = "#4a4a4a", "#d95f02", "#999999"
fig, axes = plt.subplots(2, 1, figsize=(9, 5.6), sharex=True, gridspec_kw={"hspace": 0.12})
labels = ["(a) Sectors 19, 59 and 60", "(b) The same data with the 5.31-day transits masked"]
for k, ax in enumerate(axes, start=1):
    period, sde, eligible = d[f"period{k}"], d[f"sde{k}"], d[f"eligible{k}"]
    ax.plot(period, np.where(eligible, sde, np.nan), color=INK, lw=0.45, rasterized=True)
    ax.axhline(threshold, color=GRID, ls="--", lw=0.8)
    ax.text(
        540,
        threshold + 0.35,
        f"detection threshold (SDE {threshold:g})",
        fontsize=8,
        color="#666666",
        ha="right",
    )
    ax.set_ylim(-3.5, 18.5)
    ax.set_ylabel("SDE")
    ax.text(0.99, 0.96, labels[k - 1], transform=ax.transAxes, ha="right", va="top", fontsize=9.5)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    best = np.nanargmax(np.where(eligible, sde, np.nan))
    print(f"pass {k}: best eligible SDE {sde[best]:.2f} at {period[best]:.4f} d")

ax = axes[0]
for ratio, label in ((1 / 7, "P/7"), (1 / 3, "P/3"), (1 / 2, "P/2"), (2, "2P"), (3, "3P")):
    ax.axvline(P * ratio, color=ALIAS, ls=":", lw=0.9, alpha=0.8, zorder=0)
    ax.text(P * ratio * 1.035, 13.6, label, fontsize=8, color=ALIAS)
ax.axvline(P, color=ALIAS, lw=1.0, alpha=0.35, zorder=0)
ax.text(P * 1.035, 16.4, "P = 5.3074 d", fontsize=9, color="#222222")
axes[1].axvline(P, color=ALIAS, lw=1.0, alpha=0.35, zorder=0)

axes[1].set_xscale("log")
axes[1].set_xlim(0.5, float(d["period1"].max()))
axes[1].set_xlabel("trial period (days)")
fig.savefig(OUT / "figure2.png", dpi=150, bbox_inches="tight")
print("saved figure2.png")
