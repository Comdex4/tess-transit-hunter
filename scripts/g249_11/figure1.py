"""Figure 1 of the G 249-11 note: the transit in each epoch, and every 2-minute transit.

(a)-(c): data folded at the fitted ephemeris, one panel per epoch, 15-minute bins,
with the maximum-posterior transit model from the 2-minute fit overlaid.
(d): the 13 individual 2-minute transits, 30-minute bins, offset vertically,
each with the same model.

Usage, from the repository root::

    python scripts/g249_11/figure1.py

Reads the fit from ``results/g249-11/s19-59-60/report.json`` and writes
``results/g249-11/figure1.png``. Needs network access to MAST the first time.
"""

import json
import math
import warnings
from pathlib import Path

import lightkurve as lk
import matplotlib.pyplot as plt
import numpy as np

from transit_hunter.data import fetch_lightcurve
from transit_hunter.detrend import DetrendConfig, detrend
from transit_hunter.fit import BatmanModel, q_to_u
from transit_hunter.lightcurve import LightCurve

warnings.filterwarnings("ignore")
OUT = Path(__file__).resolve().parents[2] / "results" / "g249-11"
TIC = 417732194
DET = DetrendConfig(window_length=0.75)
fit = json.loads((OUT / "s19-59-60" / "report.json").read_text())["planets"][0]["fit"]
p = fit["max_posterior_sample"]
P, T0 = p["period"], p["t0"]
a_rs = math.exp(p["ln_a_rs"])
inc = math.degrees(math.acos(min(p["b"] / a_rs, 1.0)))
u1, u2 = q_to_u(p["q1"], p["q2"])
hours = np.linspace(-3.0, 3.0, 721)
model = BatmanModel(T0 + hours / 24.0, fit["supersample"], 120.0 / 86400.0)
model_ppm = (model(T0, P, p["rp_rs"], a_rs, inc, u1, u2) - 1.0) * 1e6
print(f"model depth at mid-transit: {-model_ppm.min():.0f} ppm; b {p['b']:.2f}, a/R* {a_rs:.1f}")


def clipped(lc, nsigma=6.0):
    f = lc.flux
    s = 1.4826 * np.nanmedian(np.abs(f - np.nanmedian(f)))
    return lc.select(np.isfinite(f) & (np.abs(f - np.nanmedian(f)) < nsigma * s))


def concat(parts):
    return LightCurve(
        *(
            np.concatenate([getattr(q, k) for q in parts])
            for k in ("time", "flux", "flux_err", "sector")
        )
    )


flat = {s: detrend(fetch_lightcurve(TIC, sectors=[s]), DET).flat for s in (19, 59, 60)}
qlp = []
for item in lk.search_lightcurve(f"TIC {TIC}", mission="TESS", author="QLP"):
    s = int(item.table["sequence_number"][0])
    if s in flat:
        continue
    lc = item.download(quality_bitmask="default")
    col = "kspsap_flux" if "kspsap_flux" in lc.colnames else "sap_flux"
    t = np.asarray(lc.time.value, float)
    f = np.asarray(lc[col].value, float)
    ok = np.isfinite(t) & np.isfinite(f) & (f > 0)
    t, f = t[ok], f[ok] / np.median(f[ok])
    one = LightCurve(t, f, np.full(t.size, np.std(f)), np.full(t.size, s))
    qlp.append(clipped(detrend(one, DET).flat))
print("QLP sectors:", sorted(int(q.sector[0]) for q in qlp))


def phase_hours(time):
    return (((time - T0) / P + 0.5) % 1.0 - 0.5) * P * 24.0


def binned(x, y, width, lo=-3.0, hi=3.0):
    edges = np.arange(lo, hi + 1e-9, width)
    idx = np.digitize(x, edges) - 1
    centres, means, errs = [], [], []
    for k in range(len(edges) - 1):
        sel = idx == k
        if sel.sum() >= 3:
            centres.append(0.5 * (edges[k] + edges[k + 1]))
            means.append(np.mean(y[sel]))
            errs.append(np.std(y[sel]) / np.sqrt(sel.sum()))
    return np.array(centres), np.array(means), np.array(errs)


DATA, BIN, MODEL = "#b8b8b8", "#1f3b73", "#d95f02"
fig = plt.figure(figsize=(11, 8.2))
gs = fig.add_gridspec(3, 2, width_ratios=[1.55, 1], hspace=0.08, wspace=0.18)
epochs = [
    ("(a) Sector 19, 2019 (SPOC 2-min)", flat[19]),
    ("(b) Sectors 59–60, 2022–23 (SPOC 2-min)", concat([flat[59], flat[60]])),
    ("(c) Sectors 73 and 86, 2023–24 (QLP full-frame)", concat(qlp)),
]
axes = []
for row, (label, lc) in enumerate(epochs):
    ax = fig.add_subplot(gs[row, 0], sharex=axes[0] if axes else None)
    axes.append(ax)
    x = phase_hours(lc.time)
    y = (lc.flux - 1.0) * 1e6
    m = np.abs(x) < 3.0
    ax.plot(x[m], y[m], ".", ms=1.6, color=DATA, zorder=1)
    c, mu, e = binned(x[m], y[m], 0.25)
    level = np.median(mu[np.abs(c) > 1.0])
    ax.errorbar(c, mu - level, e, fmt="o", ms=3.5, color=BIN, lw=1, zorder=3)
    ax.plot(hours, model_ppm, color=MODEL, lw=1.6, zorder=4)
    ax.set_ylim(-6500, 4500)
    ax.text(0.01, 0.95, label, transform=ax.transAxes, fontsize=9.5, va="top")
    ax.set_ylabel("relative flux (ppm)")
    if row < 2:
        ax.tick_params(labelbottom=False)
axes[-1].set_xlabel("hours from mid-transit")
axes[0].set_xlim(-3, 3)

ax = fig.add_subplot(gs[:, 1])
step = 9000.0
transits = []
for s in (19, 59, 60):
    lc = flat[s]
    for n in np.unique(np.round((lc.time - T0) / P)):
        tc = T0 + n * P
        x = (lc.time - tc) * 24.0
        m = np.abs(x) < 3.0
        if np.sum(np.abs(x) < 0.4) >= 5 and m.sum() > 60:
            transits.append((s, tc, x[m], (lc.flux[m] - 1.0) * 1e6))
for k, (s, _tc, x, y) in enumerate(transits):
    off = -k * step
    c, mu, e = binned(x, y, 0.5)
    level = np.median(mu[np.abs(c) > 1.0])
    ax.errorbar(c, mu - level + off, e, fmt="o", ms=3, color=BIN, lw=0.8)
    ax.plot(hours, model_ppm + off, color=MODEL, lw=1.0)
    ax.text(3.1, off, f"S{s}", fontsize=7.5, va="center", color="#555555")
ax.set_xlim(-3, 3.8)
ax.set_ylim(-(len(transits) - 1) * step - 8000, 4500)
ax.set_yticks([])
ax.set_xlabel("hours from mid-transit")
ax.set_title(
    f"(d) The {len(transits)} individual 2-minute transits\n"
    f"(30-min bins, offset by {step / 1000:.0f},000 ppm)",
    fontsize=9.5,
    loc="left",
)
for a in [*axes, ax]:
    for side in ("top", "right"):
        a.spines[side].set_visible(False)
fig.savefig(OUT / "figure1.png", dpi=150, bbox_inches="tight")
print(f"saved figure1.png with {len(transits)} individual transits")
