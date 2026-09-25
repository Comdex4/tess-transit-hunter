#!/usr/bin/env python
"""Draw the two explanatory figures in the README (transit primer, depth vs radius).

These are illustrations computed from simple geometry, not pipeline results.
"""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

plt.switch_backend("Agg")

OUT = str(Path(__file__).resolve().parents[1] / "docs" / "assets" / "readme") + "/"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
YELLOW = "#eda100"
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK2,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "axes.facecolor": SURFACE,
        "figure.facecolor": SURFACE,
        "text.color": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.color": GRID,
    }
)

# ---------------- transit primer
k = 0.12
b = 0.35
u1, u2 = 0.45, 0.2
n = 900
ax_ = np.linspace(-1, 1, n)
X, Y = np.meshgrid(ax_, ax_)
R2 = X**2 + Y**2
on = R2 <= 1
mu = np.sqrt(np.clip(1 - R2, 0, 1))
I = np.where(on, 1 - u1 * (1 - mu) - u2 * (1 - mu) ** 2, 0)
tot = I.sum()
xs = np.linspace(-1.45, 1.45, 500)
flux = np.array([1 - I[((X - x) ** 2 + (Y - b) ** 2) < k**2].sum() / tot for x in xs])
x1 = np.sqrt((1 + k) ** 2 - b**2)
x2 = np.sqrt((1 - k) ** 2 - b**2)
contacts = [-x1, -x2, 0, x2, x1]
fig = plt.figure(figsize=(11, 6.4))
a0 = fig.add_axes([0.06, 0.52, 0.88, 0.40])
a1 = fig.add_axes([0.06, 0.09, 0.88, 0.40])
cmap = matplotlib.colors.LinearSegmentedColormap.from_list("s", ["#fcfcfb", "#f6d9a8", "#eda100"])
Im = np.ma.masked_where(~on, I)
a0.imshow(
    Im,
    extent=[-1, 1, -1, 1],
    origin="lower",
    cmap=matplotlib.colors.LinearSegmentedColormap.from_list(
        "st", ["#e08a1e", "#ffd27a", "#fff3d6"]
    ),
    vmin=0.3,
    vmax=1,
)
a0.plot([-1.6, 1.6], [b, b], ls="--", color=MUTED, lw=1)
for i, x in enumerate(contacts):
    a0.add_patch(Circle((x, b), k, color="#1b1b1a", zorder=3))
    a0.text(
        x, b + k + 0.08, str(i + 1), ha="center", va="bottom", fontsize=11, color=INK, weight="bold"
    )
a0.annotate("", xy=(1.55, b), xytext=(1.25, b), arrowprops=dict(arrowstyle="->", color=INK2))
a0.text(1.56, b - 0.12, "orbit", color=INK2, fontsize=10)
a0.text(
    -1.08,
    -0.6,
    "Host star\n(limb-darkened: the edge\nlooks dimmer than the centre)",
    fontsize=10,
    color=INK2,
    ha="right",
)
a0.text(
    1.08,
    -0.6,
    "Planet (Rp/R* = 0.12, exaggerated)\nimpact parameter b = 0.35",
    fontsize=10,
    color=INK2,
    ha="left",
)
a0.set_xlim(-1.65, 1.9)
a0.set_ylim(-1.05, 1.05)
a0.set_aspect("equal")
a0.axis("off")
ppm = (flux - 1) * 1e6
a1.plot(xs, ppm, color=BLUE, lw=2)
a1.grid(True, lw=0.6)
for i, x in enumerate(contacts):
    j = np.argmin(abs(xs - x))
    a1.plot(x, ppm[j], "o", ms=8, color=BLUE, mec=SURFACE, mew=2, zorder=4)
    a1.text(x, ppm[j] + 900, str(i + 1), ha="center", fontsize=11, weight="bold")
d = -ppm.min()
a1.annotate("", xy=(1.3, -d), xytext=(1.3, 0), arrowprops=dict(arrowstyle="<->", color=INK2))
a1.text(1.33, -d / 2, f"depth ≈ (Rp/R*)²\n≈ {d / 1e4:.1f} %", va="center", fontsize=10, color=INK2)
a1.annotate(
    "", xy=(-x1, -d - 2600), xytext=(x1, -d - 2600), arrowprops=dict(arrowstyle="<->", color=INK2)
)
a1.text(
    0,
    -d - 3900,
    "T14: first to fourth contact (total duration)",
    ha="center",
    fontsize=10,
    color=INK2,
)
a1.annotate(
    "", xy=(-x2, -d + 2200), xytext=(x2, -d + 2200), arrowprops=dict(arrowstyle="<->", color=MUTED)
)
a1.text(0, -d + 2700, "T23: planet fully on the disk", ha="center", fontsize=9.5, color=MUTED)
a1.set_xlim(-1.65, 1.9)
a1.set_ylim(-d - 5000, 2400)
a1.set_xlabel("time (arbitrary units; mid-transit at 0)")
a1.set_ylabel("brightness − 1 (ppm)")
fig.text(
    0.06, 0.975, "What the pipeline is looking for: a transit", fontsize=14, weight="bold", va="top"
)
fig.savefig(OUT + "transit_primer.png", dpi=150)
plt.close(fig)

# ---------------- depth vs radius
RE_RSUN = 6371 / 695700
rp = np.logspace(np.log10(0.5), np.log10(12), 300)
hosts = [
    ("M dwarf (0.38 R☉)", 0.38, BLUE),
    ("K dwarf (0.75 R☉)", 0.75, ORANGE),
    ("Sun-like G dwarf (1.0 R☉)", 1.0, AQUA),
    ("F star (1.4 R☉)", 1.4, YELLOW),
]
fig, ax = plt.subplots(figsize=(10, 5.6))
for lab, rs, c in hosts:
    dep = (rp * RE_RSUN / rs) ** 2 * 1e6
    ax.plot(rp, dep, color=c, lw=2, label=lab)
ax.set_xscale("log")
ax.set_yscale("log")
ax.axhline(140, color=INK2, lw=1, ls="--")
ax.text(
    0.53,
    98,
    "140 ppm: 1-hour scatter of the synthetic G-dwarf light curve used for completeness",
    fontsize=9.5,
    color=INK2,
    bbox=dict(fc=SURFACE, ec="none", pad=1.5),
    zorder=5,
)
for name, r in [("Earth", 1.0), ("Neptune", 3.88), ("Jupiter", 11.2)]:
    ax.axvline(r, color=GRID, lw=1, zorder=0)
    ax.text(r * 0.97, 4.5e4, name, fontsize=9.5, color=INK2, ha="right")
ax.set_xlim(0.5, 12)
ax.set_ylim(10, 7e4)
ax.set_xticks([0.5, 1, 2, 4, 8, 12])
ax.set_xticklabels(["0.5", "1", "2", "4", "8", "12"])
ax.set_xlabel("planet radius (Earth radii)")
ax.set_ylabel("transit depth (ppm)")
ax.grid(True, which="major", lw=0.6)
ax.legend(frameon=False, loc="lower right")
ax.set_title("Same planet, smaller star, deeper transit", loc="left", fontsize=14, weight="bold")
fig.tight_layout()
fig.savefig(OUT + "depth_vs_radius.png", dpi=150)
plt.close(fig)
print("wrote", OUT)
