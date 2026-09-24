"""Injection-recovery tests: how complete is the search?

Synthetic ``batman`` transits are multiplied into a light curve *before*
detrending (so that any damage the detrending does to transits is included),
then the same detrend + BLS search used on real targets is run and the result
is compared with the injected signal.

An injection counts as recovered when a *detected* signal (passing the SDE and
S/N thresholds) has

* a period within ``period_tolerance`` (default 1 %) of the injected one, and
* a mid-transit time within ``t0_tolerance`` (default 0.5) injected transit
  durations of one of the injected transits.

Signals at simple period ratios (1/2, 2, 1/3, 3) of the injection that also
line up in time are recorded as aliases; they are *not* counted as recoveries.

Parameters are drawn per cell of a period x radius grid: period and radius
log-uniformly within the cell, impact parameter uniformly in ``[0, b_max]``,
and the reference epoch uniformly within the first period. The host star's mass
and radius convert these to ``Rp/R*`` and ``a/R*`` (circular orbits).
"""

from __future__ import annotations

import csv
import logging
import math
import os
import time as _time
from collections.abc import Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any

import numpy as np

from .detrend import DetrendConfig, detrend
from .lightcurve import LightCurve
from .models import TransitParams, a_rs_from_mass_radius, t14, transit_model
from .plotting import (
    INK,
    INK_SECONDARY,
    SEQUENTIAL_CMAP,
    SURFACE,
    format_log_axis,
    new_figure,
    save_figure,
    style,
)
from .search import SearchConfig, Signal, iterative_search
from .utils import R_EARTH, R_SUN, fold, log_uniform, transit_mask

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class InjectionGrid:
    """Cell edges of the period (days) x radius (Earth radii) grid."""

    period_edges: tuple[float, ...]
    radius_edges: tuple[float, ...]
    n_per_cell: int

    @classmethod
    def log_spaced(
        cls,
        period_range: tuple[float, float],
        n_period: int,
        radius_range: tuple[float, float],
        n_radius: int,
        n_per_cell: int,
    ) -> InjectionGrid:
        periods = tuple(float(x) for x in np.geomspace(*period_range, n_period + 1))
        radii = tuple(float(x) for x in np.geomspace(*radius_range, n_radius + 1))
        return cls(periods, radii, n_per_cell)

    @property
    def shape(self) -> tuple[int, int]:
        """(n_radius, n_period): rows are radius bins, columns period bins."""
        return len(self.radius_edges) - 1, len(self.period_edges) - 1

    @property
    def size(self) -> int:
        n_r, n_p = self.shape
        return n_r * n_p * self.n_per_cell


@dataclass
class Injection:
    index: int
    period_bin: int
    radius_bin: int
    period: float
    radius_earth: float
    t0: float
    b: float
    rp_rs: float
    a_rs: float
    duration: float  # T14, days
    u1: float
    u2: float

    def params(self) -> TransitParams:
        return TransitParams(self.t0, self.period, self.rp_rs, self.a_rs, self.b, self.u1, self.u2)


def draw_injections(
    grid: InjectionGrid,
    star_radius: float,
    star_mass: float,
    t_start: float,
    seed: int = 0,
    b_max: float = 0.9,
    limb_darkening: tuple[float, float] = (0.4, 0.2),
) -> list[Injection]:
    """Draw ``grid.n_per_cell`` injections in every cell (deterministic for a seed)."""
    rng = np.random.default_rng(seed)
    out: list[Injection] = []
    n_r, n_p = grid.shape
    for i in range(n_r):
        for j in range(n_p):
            for _ in range(grid.n_per_cell):
                period = float(log_uniform(rng, grid.period_edges[j], grid.period_edges[j + 1]))
                radius = float(log_uniform(rng, grid.radius_edges[i], grid.radius_edges[i + 1]))
                b = float(rng.uniform(0.0, b_max))
                t0 = float(t_start + rng.uniform(0.0, period))
                rp_rs = radius * R_EARTH / (star_radius * R_SUN)
                a_rs = a_rs_from_mass_radius(period, star_mass, star_radius)
                out.append(
                    Injection(
                        index=len(out),
                        period_bin=j,
                        radius_bin=i,
                        period=period,
                        radius_earth=radius,
                        t0=t0,
                        b=b,
                        rp_rs=rp_rs,
                        a_rs=a_rs,
                        duration=t14(period, a_rs, rp_rs, b),
                        u1=limb_darkening[0],
                        u2=limb_darkening[1],
                    )
                )
    return out


def inject(lc: LightCurve, injection: Injection) -> LightCurve:
    """Multiply a transit into the (un-detrended) flux."""
    cadence = lc.cadence
    supersample = max(1, math.ceil(cadence * 1440 / 2.0 - 1e-6))
    model = transit_model(
        lc.time,
        injection.params(),
        supersample_factor=supersample,
        exp_time=cadence if supersample > 1 else 0.0,
    )
    return lc.with_flux(lc.flux * model, injected=asdict(injection))


@dataclass(frozen=True)
class RecoveryCriteria:
    period_tolerance: float = 0.01
    t0_tolerance: float = 0.5  # injected transit durations


def match_signal(
    injection: Injection, signal: Signal, criteria: RecoveryCriteria | None = None
) -> str:
    """Classify a detected signal as 'exact' match, 'alias', or 'none'."""
    criteria = criteria or RecoveryCriteria()
    tolerance_t = criteria.t0_tolerance * max(injection.duration, 1e-3)
    for ratio, label in (
        (1, "exact"),
        (1 / 2, "alias"),
        (2, "alias"),
        (1 / 3, "alias"),
        (3, "alias"),
    ):
        expected = injection.period * ratio
        if abs(signal.period - expected) > criteria.period_tolerance * expected:
            continue
        # The signal's transits must coincide in time with injected transits. For a
        # signal at P/m only every m-th signal transit is a real event, so check the
        # m consecutive signal epochs.
        m = round(1 / ratio) if ratio < 1 else 1
        epochs = signal.t0 + signal.period * np.arange(m)
        offsets = np.abs(fold(epochs, injection.period, injection.t0))
        if offsets.min() < tolerance_t:
            return label
    return "none"


# --------------------------------------------------------------------------- execution
_WORKER_STATE: dict[str, Any] = {}


def _worker_init(
    lc: LightCurve,
    detrend_cfg: DetrendConfig,
    search_cfg: SearchConfig,
    criteria: RecoveryCriteria,
    mask: np.ndarray | None,
) -> None:
    _WORKER_STATE.update(
        lc=lc, detrend=detrend_cfg, search=search_cfg, criteria=criteria, mask=mask
    )


def run_one(
    injection: Injection,
    lc: LightCurve,
    detrend_cfg: DetrendConfig,
    search_cfg: SearchConfig,
    criteria: RecoveryCriteria,
    mask: np.ndarray | None = None,
) -> dict[str, Any]:
    """Inject, detrend, search, and compare. Returns one result row."""
    start = _time.perf_counter()
    injected = inject(lc, injection)
    if mask is not None:  # e.g. transits of known planets in a real light curve
        injected = injected.select(~mask)
    flat = detrend(injected, detrend_cfg).flat
    result = iterative_search(flat, search_cfg, raw=injected, detrend_config=detrend_cfg)
    status, best = "none", None
    for sig in result.signals:
        if not sig.detected:
            continue
        kind = match_signal(injection, sig, criteria)
        if kind == "exact":
            status, best = kind, sig
            break
        if kind == "alias" and status == "none":
            status, best = kind, sig
    top = result.signals[0] if result.signals else None
    ref = best or top
    in_data = transit_mask(flat.time, injection.period, injection.t0, injection.duration)
    n_transits_in_data = int(
        np.unique(np.round((flat.time[in_data] - injection.t0) / injection.period)).size
    )
    row = asdict(injection)
    row.update(
        recovered=status == "exact",
        match=status,
        n_transits_in_data=n_transits_in_data,
        found_period=ref.period if ref else float("nan"),
        found_t0=ref.t0 if ref else float("nan"),
        found_depth=ref.depth if ref else float("nan"),
        found_sde=ref.sde if ref else float("nan"),
        found_snr=ref.snr if ref else float("nan"),
        found_detected=bool(ref.detected) if ref else False,
        n_detections=len(result.detections),
        runtime_s=_time.perf_counter() - start,
    )
    return row


def _run_from_state(injection: Injection) -> dict[str, Any]:
    s = _WORKER_STATE
    return run_one(injection, s["lc"], s["detrend"], s["search"], s["criteria"], s["mask"])


RESULT_FIELDS = [f.name for f in fields(Injection)] + [
    "recovered",
    "match",
    "n_transits_in_data",
    "found_period",
    "found_t0",
    "found_depth",
    "found_sde",
    "found_snr",
    "found_detected",
    "n_detections",
    "runtime_s",
]


def read_results(path: str | Path) -> list[dict[str, Any]]:
    """Load a results CSV written by :func:`run_injections` (types restored)."""
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    with path.open(newline="") as handle:
        for raw in csv.DictReader(handle):
            row: dict[str, Any] = {}
            for key, value in raw.items():
                if key in ("recovered", "found_detected"):
                    row[key] = value == "True"
                elif key == "match":
                    row[key] = value
                elif key in (
                    "index",
                    "period_bin",
                    "radius_bin",
                    "n_transits_in_data",
                    "n_detections",
                ):
                    row[key] = int(value)
                else:
                    row[key] = float(value) if value not in ("", "nan") else float("nan")
            rows.append(row)
    return rows


def run_injections(
    lc: LightCurve,
    injections: Sequence[Injection],
    out_csv: str | Path,
    detrend_cfg: DetrendConfig | None = None,
    search_cfg: SearchConfig | None = None,
    criteria: RecoveryCriteria | None = None,
    mask: np.ndarray | None = None,
    n_workers: int | None = None,
) -> list[dict[str, Any]]:
    """Run all injections in parallel, appending rows to ``out_csv`` as they finish.

    Already-completed injection indices in ``out_csv`` are skipped, so an
    interrupted run can be resumed by calling this again.
    """
    detrend_cfg = detrend_cfg or DetrendConfig()
    search_cfg = replace(search_cfg or SearchConfig(max_signals=2), n_workers=1)
    criteria = criteria or RecoveryCriteria()
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    done = {row["index"] for row in read_results(out_csv)}
    todo = [inj for inj in injections if inj.index not in done]
    n_workers = n_workers or os.cpu_count() or 1
    log.info(
        "%d injections to run (%d already done) on %d workers", len(todo), len(done), n_workers
    )

    new_file = not out_csv.exists() or out_csv.stat().st_size == 0
    with out_csv.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        if new_file:
            writer.writeheader()
        if n_workers == 1:
            for i, inj in enumerate(todo, 1):
                writer.writerow(run_one(inj, lc, detrend_cfg, search_cfg, criteria, mask))
                handle.flush()
                _progress(i, len(todo))
        else:
            with ProcessPoolExecutor(
                max_workers=n_workers,
                initializer=_worker_init,
                initargs=(lc, detrend_cfg, search_cfg, criteria, mask),
            ) as pool:
                futures = [pool.submit(_run_from_state, inj) for inj in todo]
                for i, future in enumerate(as_completed(futures), 1):
                    writer.writerow(future.result())
                    handle.flush()
                    _progress(i, len(todo))
    rows = read_results(out_csv)
    wanted = {inj.index for inj in injections}
    return [row for row in rows if row["index"] in wanted]


def _progress(done: int, total: int) -> None:
    if done == total or done % max(1, total // 20) == 0:
        log.info("injections: %d / %d", done, total)


# --------------------------------------------------------------------------- summaries
@dataclass
class CompletenessTable:
    grid: InjectionGrid
    recovered: np.ndarray  # (n_radius, n_period) counts
    total: np.ndarray
    aliases: np.ndarray

    @property
    def fraction(self) -> np.ndarray:
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(self.total > 0, self.recovered / self.total, np.nan)

    @property
    def overall(self) -> float:
        return float(self.recovered.sum() / max(self.total.sum(), 1))

    def as_dict(self) -> dict[str, Any]:
        return {
            "period_edges": list(self.grid.period_edges),
            "radius_edges": list(self.grid.radius_edges),
            "recovered": self.recovered.tolist(),
            "total": self.total.tolist(),
            "aliases": self.aliases.tolist(),
            "fraction": [
                [None if not np.isfinite(v) else float(v) for v in row] for row in self.fraction
            ],
            "overall_fraction": self.overall,
            "n_injections": int(self.total.sum()),
        }


def completeness(rows: Iterable[dict[str, Any]], grid: InjectionGrid) -> CompletenessTable:
    n_r, n_p = grid.shape
    recovered = np.zeros((n_r, n_p), dtype=int)
    total = np.zeros((n_r, n_p), dtype=int)
    aliases = np.zeros((n_r, n_p), dtype=int)
    for row in rows:
        i, j = int(row["radius_bin"]), int(row["period_bin"])
        total[i, j] += 1
        recovered[i, j] += bool(row["recovered"])
        aliases[i, j] += row.get("match") == "alias"
    return CompletenessTable(grid, recovered, total, aliases)


def completeness_markdown(table: CompletenessTable) -> str:
    """The completeness grid as a Markdown table (rows: radius bins, columns: period bins)."""
    pe, re_ = table.grid.period_edges, table.grid.radius_edges
    header = (
        "| R_p (R⊕) \\ P (d) | "
        + " | ".join(f"{pe[j]:.3g}–{pe[j + 1]:.3g}" for j in range(len(pe) - 1))
        + " |"
    )
    lines = [header, "|" + "---|" * (len(pe))]
    frac = table.fraction
    for i in reversed(range(len(re_) - 1)):
        cells = []
        for j in range(len(pe) - 1):
            if table.total[i, j] == 0:
                cells.append("–")
            else:
                cells.append(
                    f"{100 * frac[i, j]:.0f}% ({table.recovered[i, j]}/{table.total[i, j]})"
                )
        lines.append(f"| {re_[i]:.3g}–{re_[i + 1]:.3g} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def plot_completeness(table: CompletenessTable, path: str | Path, title: str = "") -> Path:
    """Heatmap of recovery fraction with 50 % and 90 % contours."""
    pe = np.asarray(table.grid.period_edges)
    re_ = np.asarray(table.grid.radius_edges)
    frac = np.ma.masked_invalid(table.fraction)
    with style():
        fig, axes = new_figure(1, 1, figsize=(8.2, 5.6))
        ax = axes[0, 0]
        mesh = ax.pcolormesh(
            pe, re_, frac, cmap=SEQUENTIAL_CMAP, vmin=0, vmax=1, edgecolors=SURFACE, linewidth=1.5
        )
        centers_p = np.sqrt(pe[:-1] * pe[1:])
        centers_r = np.sqrt(re_[:-1] * re_[1:])
        if frac.count() > 3 and min(frac.shape) > 1:
            cs = ax.contour(
                centers_p,
                centers_r,
                frac.filled(np.nan),
                levels=[0.5, 0.9],
                colors=[INK_SECONDARY, INK],
                linewidths=[1.2, 1.6],
            )
            ax.clabel(cs, fmt={0.5: "50%", 0.9: "90%"}, fontsize=8)
        ax.set_xscale("log")
        ax.set_yscale("log")
        format_log_axis(ax, "x")
        format_log_axis(ax, "y")
        ax.set_xlim(pe[0], pe[-1])
        ax.set_ylim(re_[0], re_[-1])
        ax.set_xlabel("orbital period (days)")
        ax.set_ylabel("planet radius (R⊕)")
        ax.grid(False)
        cbar = fig.colorbar(mesh, ax=ax, pad=0.02)
        cbar.set_label("fraction recovered")
        cbar.outline.set_visible(False)
        n = int(table.total.sum())
        ax.set_title(
            (title + "\n" if title else "") + f"{n} injections, {table.grid.n_per_cell} per cell; "
            f"overall recovery {100 * table.overall:.1f}%",
            loc="left",
            fontsize=10,
        )
        return save_figure(fig, path)
