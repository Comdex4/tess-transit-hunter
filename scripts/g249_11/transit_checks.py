"""G 249-11 (TIC 417732194): individual transits, odd/even, phase 0.5, and the chance of the
other-years match.

1. Joint ephemeris from a box search of all data (2-min sectors 19, 59, 60; QLP 73, 86).
2. Every transit's depth against a line fitted to its flanks, with its distance to the
   nearest data gap and momentum dump.
3. Odd and even transits, and the flux at phase 0.5, over all data.
4. Empirical false-alarm level: the same ±0.5 % search on the other-years data alone
   (sectors 19, 73, 86) around N random periods; how often does it reach the S/N found
   at the candidate's period?
5. Figure: the fold of each data set, and every 2-minute transit.

Usage, from the repository root (N defaults to 100)::

    python scripts/g249_11/transit_checks.py N | tee results/g249-11/transit_checks.txt

The figure goes to ``results/g249-11/transit_checks.png``. Needs network access to MAST
the first time; the light curves are cached after that.
"""

import sys
import warnings
from pathlib import Path

import lightkurve as lk
import matplotlib.pyplot as plt
import numpy as np
from astropy.timeseries import BoxLeastSquares

from transit_hunter.data import fetch_lightcurve
from transit_hunter.detrend import DetrendConfig, detrend
from transit_hunter.lightcurve import LightCurve

warnings.filterwarnings("ignore")
OUT = Path(__file__).resolve().parents[2] / "results" / "g249-11"
TIC, P0, DUR = 417732194, 5.306735, 0.7 / 24
N_RANDOM = int(sys.argv[1]) if len(sys.argv) > 1 else 100
DET = DetrendConfig(window_length=0.75)


def clipped(lc, nsigma=6.0):
    f = lc.flux
    s = 1.4826 * np.nanmedian(np.abs(f - np.nanmedian(f)))
    return lc.select(np.isfinite(f) & (np.abs(f - np.nanmedian(f)) < nsigma * s))


def concat(parts):
    return LightCurve(
        *(
            np.concatenate([getattr(p, k) for p in parts])
            for k in ("time", "flux", "flux_err", "sector")
        )
    )


raw = {s: fetch_lightcurve(TIC, sectors=[s]) for s in (19, 59, 60)}
flat = {s: detrend(raw[s], DET).flat for s in raw}
dumps = np.array(sorted(t for s in raw for t in raw[s].meta.get("momentum_dumps", [])))
qlp = {}
for item in lk.search_lightcurve(f"TIC {TIC}", mission="TESS", author="QLP"):
    s = int(item.table["sequence_number"][0])
    if s in (19, 59, 60):
        continue
    lc = item.download(quality_bitmask="default")
    col = "kspsap_flux" if "kspsap_flux" in lc.colnames else "sap_flux"
    t = np.asarray(lc.time.value, float)
    f = np.asarray(lc[col].value, float)
    ok = np.isfinite(t) & np.isfinite(f) & (f > 0)
    t, f = t[ok], f[ok] / np.median(f[ok])
    one = LightCurve(t, f, np.full(t.size, np.std(f)), np.full(t.size, s))
    qlp[s] = clipped(detrend(one, DET).flat)
print("QLP sectors:", sorted(qlp))
other = concat([flat[19], *qlp.values()])
everything = concat([flat[19], flat[59], flat[60], *qlp.values()])


def search(lc, p0, window=0.005):
    t, f, sec = lc.time, lc.flux, lc.sector
    dy = np.zeros(t.size)
    for s in np.unique(sec):
        m = sec == s
        dy[m] = 1.4826 * np.median(np.abs(f[m] - np.median(f[m])))
    durations = np.clip(DUR * np.array([0.6, 0.8, 1.0, 1.3, 1.7]), 0.01, 0.4 * p0)
    baseline = t[-1] - t[0]
    freqs = np.arange(
        1 / (p0 * (1 + window)), 1 / (p0 * (1 - window)), durations.min() / (3 * baseline * p0)
    )
    r = BoxLeastSquares(t, f, dy=dy).power(1 / freqs, durations, objective="snr")
    i = int(np.argmax(r.depth_snr))
    return r.period[i], r.duration[i], r.transit_time[i], r.depth[i], r.depth_snr[i]


P, D, T0, depth, snr = search(everything, P0)
print(
    f"joint: P {P:.6f} d, T14 {D * 24:.2f} h, T0 {T0:.4f}, depth {depth * 1e6:.0f} ppm, "
    f"S/N {snr:.1f}"
)

# 2. individual transits
print("individual transits (depth against a line fitted to 0.75-3 durations either side):")
rows = []
sets = [("s19", flat[19]), ("s59", flat[59]), ("s60", flat[60])]
for name, lc in sets + [(f"QLP s{s}", q) for s, q in qlp.items()]:
    t, f = lc.time, lc.flux
    gaps = np.flatnonzero(np.diff(t) > 0.1)
    edges = np.concatenate([[t[0]], t[gaps], t[gaps + 1], [t[-1]]])
    for n in np.unique(np.round((t - T0) / P)):
        tc = T0 + n * P
        dt = t - tc
        inside = np.abs(dt) < 0.4 * D
        flank = (np.abs(dt) > 0.75 * D) & (np.abs(dt) < 3 * D)
        if inside.sum() < 3 or flank.sum() < 10:
            continue
        coef = np.polyfit(dt[flank], f[flank], 1)
        resid = f[flank] - np.polyval(coef, dt[flank])
        sig = 1.4826 * np.median(np.abs(resid - np.median(resid)))
        d = np.polyval(coef, 0) - np.mean(f[inside])
        e = sig * np.sqrt(1 / inside.sum() + 1 / flank.sum())
        edge = np.min(np.abs(edges - tc)) * 24
        dump = np.min(np.abs(dumps - tc)) * 24 if dumps.size else np.nan
        rows.append((name, int(n), tc, d, e, edge, dump))
        print(
            f"  {name:8s} epoch {int(n):4d} BTJD {tc:9.3f}: {d * 1e6:6.0f} ± {e * 1e6:4.0f} ppm  "
            f"edge {edge:6.1f} h  dump {dump:6.1f} h"
        )
for name in ("s19", "s59", "s60"):
    sel = [r for r in rows if r[0] == name]
    if sel:
        d = np.array([r[3] for r in sel])
        e = np.array([r[4] for r in sel])
        w = 1 / e**2
        mean = np.sum(w * d) / np.sum(w)
        print(
            f"  {name}: {mean * 1e6:.0f} ± {1 / np.sqrt(np.sum(w)) * 1e6:.0f} ppm from "
            f"{len(sel)} transits, chi2 {np.sum(w * (d - mean) ** 2):.1f} for {len(sel) - 1} dof"
        )

# 3. odd/even and phase 0.5 over all data
t, f = everything.time, everything.flux
ph2 = ((t - T0) / P) % 2.0
for label, centre in (("odd", 0.0), ("even", 1.0), ("phase 0.5", 0.5), ("phase 1.5", 1.5)):
    d = np.abs(((ph2 - centre + 1.0) % 2.0) - 1.0) * P
    inside = d < 0.4 * D
    out = (d > 0.75 * D) & (d < 4 * D)
    sig = 1.4826 * np.median(np.abs(f[out] - np.median(f[out])))
    dep = np.mean(f[out]) - np.mean(f[inside])
    err = sig * np.sqrt(1 / inside.sum() + 1 / out.sum())
    print(f"  {label:9s}: {dep * 1e6:6.0f} ± {err * 1e6:4.0f} ppm")

# 4. how often do the other years alone reach this S/N at a random period?
p_o, _, _, d_o, snr_o = search(other, P0)
print(
    f"other years alone at the candidate's period: P {p_o:.6f} "
    f"({(p_o / P - 1) * 1e6:+.0f} ppm of P), S/N {snr_o:.1f}"
)
rng = np.random.default_rng(2)
fake = []
while len(fake) < N_RANDOM:
    p = P0 * np.exp(rng.uniform(np.log(1 / 1.5), np.log(1.5)))
    if min(abs(p / P0 - r) for r in (1.0, 0.5, 2.0, 1 / 3, 3.0, 2 / 3, 1.5)) < 0.01:
        continue
    fake.append(search(other, p)[4])
fake = np.array(fake)
print(
    f"  {N_RANDOM} random windows: max S/N median {np.median(fake):.1f}, 95th percentile "
    f"{np.percentile(fake, 95):.1f}, highest {fake.max():.1f}; "
    f"share >= {snr_o:.1f}: {np.mean(fake >= snr_o):.3f}"
)

# 5. figure
fig = plt.figure(figsize=(16, 8))
gs = fig.add_gridspec(2, 1, height_ratios=[1, 1])
top = gs[0].subgridspec(1, 3)
groups = [
    ("2019: sector 19 (2-min)", flat[19]),
    ("2022: sectors 59-60 (2-min, the batch)", concat([flat[59], flat[60]])),
    (
        "2023-24: sectors " + ", ".join(map(str, sorted(qlp))) + " (QLP full-frame)",
        concat(list(qlp.values())),
    ),
]
for k, (label, lc) in enumerate(groups):
    ax = fig.add_subplot(top[k])
    x = (((lc.time - T0) / P + 0.5) % 1.0 - 0.5) * P * 24
    m = np.abs(x) < 4
    ax.plot(x[m], (lc.flux[m] - 1) * 1e6, ".", ms=1.5, color="0.75")
    edges_h = np.arange(-4, 4.01, 0.25)
    idx = np.digitize(x[m], edges_h) - 1
    b = [np.mean(lc.flux[m][idx == j]) for j in range(len(edges_h) - 1)]
    e = [
        np.std(lc.flux[m][idx == j]) / np.sqrt(max((idx == j).sum(), 1))
        for j in range(len(edges_h) - 1)
    ]
    ax.errorbar(
        0.5 * (edges_h[1:] + edges_h[:-1]),
        (np.array(b) - 1) * 1e6,
        np.array(e) * 1e6,
        fmt="o",
        color="C0",
        ms=4,
    )
    ax.axvspan(-D * 12, D * 12, color="C1", alpha=0.15)
    ax.set_ylim(-7000, 4000)
    ax.set_title(label, fontsize=10)
    ax.set_xlabel("hours from mid-transit")
    if k == 0:
        ax.set_ylabel("ppm")
bottom = gs[1].subgridspec(1, max(1, len([r for r in rows if not r[0].startswith("QLP")])))
for k, r in enumerate([r for r in rows if not r[0].startswith("QLP")]):
    ax = fig.add_subplot(bottom[k])
    lc = flat[int(r[0][1:])]
    x = (lc.time - r[2]) * 24
    m = np.abs(x) < 4
    ax.plot(x[m], (lc.flux[m] - 1) * 1e6, ".", ms=2, color="0.6")
    edges_h = np.arange(-4, 4.01, 0.5)
    idx = np.digitize(x[m], edges_h) - 1
    b = [
        np.mean(lc.flux[m][idx == j]) if np.any(idx == j) else np.nan
        for j in range(len(edges_h) - 1)
    ]
    ax.plot(0.5 * (edges_h[1:] + edges_h[:-1]), (np.array(b) - 1) * 1e6, "o", color="C0", ms=3)
    ax.axvspan(-D * 12, D * 12, color="C1", alpha=0.15)
    ax.set_ylim(-12000, 8000)
    ax.set_xticks([-3, 0, 3])
    ax.tick_params(labelsize=7)
    ax.set_title(f"{r[0]}\n{r[3] * 1e6:.0f}±{r[4] * 1e6:.0f}", fontsize=7)
    if k:
        ax.set_yticklabels([])
fig.suptitle(
    f"TIC 417732194: P = {P:.5f} d, T14 = {D * 24:.1f} h; top: folds by year (orange: transit); "
    "bottom: each 2-minute transit (ppm)"
)
fig.tight_layout()
fig.savefig(OUT / "transit_checks.png", dpi=80)
