"""Detect the transit of G 249-11 (TIC 417732194) with Transit Least Squares.

TLS (Hippke & Heller 2019, A&A 623, A39) searches four sets of the light curves prepared
by ``tess_data.py``, each over periods of 0.5-20 days:

  discovery  sectors 59 and 60, where the batch search found the signal
  2min       sectors 19, 59 and 60: all the 2-minute data
  others     sectors 19, 73 and 86: every sector outside the discovery sectors
  all        all five sectors

The period grid uses the TIC 8 radius and mass, the duration grid their 3-sigma range,
and the transit template the star's quadratic limb darkening from TLS's TESS table
(Claret 2017). The exact backend is used (``backend="fused"``). For each set the script
prints the highest peak (period, SDE and its false-alarm probability, mid-transit time,
fitted depth), the number of transits with data, the five highest peaks, and the rank
and SDE of the candidate's period.

TLS is used here for detection only. It converts its trial durations to days on the
assumption that the data are close to continuous, which light curves spread over five
years are not (it gives 0.07 h for the 2-minute set), so its duration and the
statistics that depend on it (its S/N, in-transit depths, odd/even comparison) are not
reported; LEO-Vetter measures those (``leo_vetter_run.py``). The transits with data are
counted here as the epochs with at least 10 points within half the fitted duration
(0.86 h, ``s19-59-60/report.json``) of mid-transit.

Usage, from the repository root (needs ``pip install transitleastsquares``)::

    python scripts/g249_11/tls_search.py | tee results/g249-11/tls/tls_search.txt

Writes ``results/g249-11/tls/<set>.json`` and ``results/g249-11/tls/periodograms.png``.
"""

import json
import time
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import tess_data
from transitleastsquares import __version__ as tls_version
from transitleastsquares import catalog_info, transitleastsquares

warnings.filterwarnings("ignore")
OUT = Path(__file__).resolve().parents[2] / "results" / "g249-11" / "tls"
SETS = {
    "discovery": (59, 60),
    "2min": (19, 59, 60),
    "others": (19, 73, 86),
    "all": (19, 59, 60, 73, 86),
}
CANDIDATE_PERIOD = 5.30742  # days, from the pipeline's search of the 2-minute data
PERIOD_MIN, PERIOD_MAX = 0.5, 20.0
MIN_POINTS_IN_TRANSIT = 10


def transits_with_data(t, period, t0, t14):
    """Epochs with at least MIN_POINTS_IN_TRANSIT points within t14/2 of mid-transit."""
    epochs = np.round((t - t0) / period)
    inside = np.abs(t - t0 - epochs * period) < t14 / 2
    _, counts = np.unique(epochs[inside], return_counts=True)
    return int(np.sum(counts >= MIN_POINTS_IN_TRANSIT))


def peaks(periods, power, n=5, separation=0.01):
    """The n highest local maxima, at least ``separation`` (fractional) apart."""
    order = np.argsort(power)[::-1]
    found = []
    for i in order:
        if all(abs(periods[i] / p - 1) > separation for p, _ in found):
            found.append((float(periods[i]), float(power[i])))
        if len(found) == n:
            break
    return found


def search(name, sectors, star, t14):
    t, _, flux, err = tess_data.joined(sectors)
    model = transitleastsquares(t, flux, err, verbose=False)
    start = time.time()
    r = model.power(
        period_min=PERIOD_MIN,
        period_max=PERIOD_MAX,
        R_star=star["radius"],
        R_star_min=star["radius"] - 3 * star["radius_err"],
        R_star_max=star["radius"] + 3 * star["radius_err"],
        M_star=star["mass"],
        M_star_min=star["mass"] - 3 * star["mass_err"],
        M_star_max=star["mass"] + 3 * star["mass_err"],
        u=star["u"],
        use_threads=4,
        backend="fused",
        show_progress_bar=False,
    )
    seconds = time.time() - start
    periods, power = np.asarray(r.periods), np.asarray(r.power)
    near = np.abs(periods / CANDIDATE_PERIOD - 1) < 0.002
    candidate_sde = float(power[near].max())
    top = peaks(periods, power)
    rank = 1 + sum(p > candidate_sde and abs(q / CANDIDATE_PERIOD - 1) > 0.002 for q, p in top)
    summary = {
        "set": name,
        "sectors": list(sectors),
        "n_points": int(t.size),
        "n_periods": int(periods.size),
        "seconds": round(seconds, 1),
        "period": float(r.period),
        "period_uncertainty": float(r.period_uncertainty),
        "T0_btjd": float(r.T0),
        "SDE": float(r.SDE),
        "FAP": float(r.FAP),
        "depth_fit_ppm": float((1 - r.depth) * 1e6),
        "rp_rs": float(r.rp_rs),
        "transits_with_data": transits_with_data(t, r.period, r.T0, t14),
        "top_peaks": [{"period": p, "SDE": s} for p, s in top],
        "candidate_period_SDE": candidate_sde,
        "candidate_period_rank": rank,
    }
    (OUT / f"{name}.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"\n== {name}: sectors {', '.join(map(str, sectors))} ({t.size} points)")
    print(f"   {periods.size} trial periods, {seconds:.0f} s")
    print(
        f"   highest peak: P = {r.period:.5f} ± {r.period_uncertainty:.5f} d, "
        f"SDE {r.SDE:.1f} (FAP {r.FAP:.1e}), T0 BTJD {r.T0:.4f}"
    )
    print(
        f"   fitted depth {summary['depth_fit_ppm']:.0f} ppm (Rp/R* {r.rp_rs:.4f}); "
        f"{summary['transits_with_data']} transits with data"
    )
    print("   five highest peaks: " + ", ".join(f"{p:.5f} d (SDE {s:.1f})" for p, s in top))
    print(f"   at {CANDIDATE_PERIOD} d: SDE {candidate_sde:.1f}, rank {rank}")
    return periods, power


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ab, *_ = catalog_info(TIC_ID=tess_data.TIC)
    star = dict(tess_data.STAR, u=[float(ab[0]), float(ab[1])])
    print(f"TLS {tls_version}; TIC {tess_data.TIC}")
    print(
        f"R* = {star['radius']:.3f} ± {star['radius_err']:.3f} Rsun, "
        f"M* = {star['mass']:.3f} ± {star['mass_err']:.3f} Msun, "
        f"quadratic limb darkening u = {star['u'][0]:.4f}, {star['u'][1]:.4f}"
    )
    report = json.loads((OUT.parent / "s19-59-60" / "report.json").read_text())
    t14 = report["planets"][0]["fit"]["posterior"]["t14_hours"]["median"] / 24
    data = tess_data.load(tess_data.SPOC_SECTORS + tess_data.QLP_SECTORS)
    spectra = {}
    for name, sectors in SETS.items():
        spectra[name] = search(name, {s: data[s] for s in sectors}, star, t14)

    fig, axes = plt.subplots(len(SETS), 1, figsize=(7.2, 8.4), sharex=True)
    for ax, (name, (periods, power)) in zip(axes, spectra.items(), strict=True):
        ax.plot(periods, power, color="0.2", lw=0.5)
        ax.axvline(CANDIDATE_PERIOD, color="tab:orange", lw=1, alpha=0.5, zorder=0)
        sectors = ", ".join(map(str, SETS[name]))
        ax.set_title(f"{name}: sectors {sectors}", fontsize=9, loc="left")
        ax.set_ylabel("SDE")
    axes[-1].set_xscale("log")
    axes[-1].set_xlabel("Period (days)")
    fig.tight_layout()
    fig.savefig(OUT / "periodograms.png", dpi=150)


if __name__ == "__main__":
    main()
