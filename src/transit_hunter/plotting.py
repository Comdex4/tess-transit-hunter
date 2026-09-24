"""Shared figure styling.

All figures are built with :class:`matplotlib.figure.Figure` directly (no pyplot
state machine), so plotting is safe in headless environments, worker processes,
and CI. Colours come from a validated colour-blind-safe categorical palette
(blue / orange / aqua for up to three series), with text kept in neutral ink
colours, hairline solid gridlines, and a single-hue blue ramp for magnitudes.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import matplotlib as mpl
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure

# Categorical series colours, assigned in this fixed order (never cycled).
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
SERIES = (BLUE, ORANGE, AQUA)

# Neutral chrome and ink.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

# Status colours: only ever used to mean pass / warn / fail, always with a text label.
STATUS_GOOD = "#0ca30c"
STATUS_WARNING = "#fab219"
STATUS_CRITICAL = "#d03b3b"

# Single-hue sequential ramp (light = low, dark = high) for heatmaps.
SEQUENTIAL_BLUE = (
    "#cde2fb",
    "#b7d3f6",
    "#9ec5f4",
    "#86b6ef",
    "#6da7ec",
    "#5598e7",
    "#3987e5",
    "#2a78d6",
    "#256abf",
    "#1c5cab",
    "#184f95",
    "#104281",
    "#0d366b",
)
SEQUENTIAL_CMAP = LinearSegmentedColormap.from_list("th_blue", SEQUENTIAL_BLUE)

_RC = {
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS,
    "axes.linewidth": 0.8,
    "axes.labelcolor": INK_SECONDARY,
    "axes.titlecolor": INK,
    "axes.titlesize": 11,
    "axes.titleweight": "normal",
    "axes.labelsize": 10,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "grid.linestyle": "-",
    "xtick.color": INK_MUTED,
    "ytick.color": INK_MUTED,
    "xtick.labelcolor": INK_SECONDARY,
    "ytick.labelcolor": INK_SECONDARY,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.frameon": False,
    "legend.fontsize": 9,
    "legend.labelcolor": INK_SECONDARY,
    "font.family": "sans-serif",
    "font.size": 10,
    "text.color": INK,
    "lines.linewidth": 1.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
}


@contextmanager
def style() -> Iterator[None]:
    """Context manager applying the house style to figures created inside it."""
    with mpl.rc_context(_RC):
        yield


def new_figure(
    nrows: int = 1, ncols: int = 1, figsize: tuple[float, float] = (8.0, 4.5), **kwargs
) -> tuple[Figure, np.ndarray]:
    """Create a styled figure; returns ``(fig, axes)`` with ``axes`` always a 2-D array.

    Must be called inside :func:`style` so the rc parameters apply.
    """
    fig = Figure(figsize=figsize, layout="constrained")
    axes = fig.subplots(nrows, ncols, squeeze=False, **kwargs)
    return fig, axes


def save_figure(fig: Figure, path: str | Path, dpi: int = 150) -> Path:
    """Save ``fig`` to ``path`` (parent folders are created)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi)
    return path


def ppm_axis_label(what: str = "Relative flux") -> str:
    return f"{what} − 1 (ppm)"


def format_log_axis(ax, axis: str = "x") -> None:
    """Label a logarithmic axis with plain numbers at 1-2-5 steps (…, 1, 2, 5, 10, …)."""
    from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

    target = ax.xaxis if axis == "x" else ax.yaxis
    target.set_major_locator(LogLocator(base=10.0, subs=(1.0, 2.0, 5.0)))
    target.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    target.set_minor_formatter(NullFormatter())
