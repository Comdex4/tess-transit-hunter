"""False-positive probabilities for G 249-11 (TIC 417732194) with TRICERATOPS.

TRICERATOPS (Giacalone et al. 2021, AJ 161, 24) computes the Bayesian probability of each
scenario that could produce the transit: a planet or an eclipsing binary on the target,
on an unresolved bound or chance-aligned star, or on any resolved star within 10 TESS
pixels. It uses the TESS pixels (TESScut cutouts and the SPOC apertures), the TIC, the
Gaia DR3 field population, and the shape of the transit. It returns the false-positive
probability (FPP) and the nearby false-positive probability (NFPP); Giacalone et al.
(2021) call a planet validated at FPP < 0.015 and NFPP < 0.001, and likely at FPP < 0.5
and NFPP < 0.001.

Input: the 2-minute PDCSAP data of sectors 19, 59 and 60 (``tess_data.py``; corrected for
dilution by SPOC), folded at the TLS ephemeris of those sectors (``tls/2min.json``),
within 3 hours of mid-transit, in 5-minute bins; the SPOC apertures of those sectors;
and the transit depth fitted by TLS. There is no high-resolution imaging of the star
yet, so no contrast curve is used.

The scenarios are drawn at random, so the calculation is repeated (10 times by default)
and the mean and standard deviation of FPP and NFPP are reported.

Usage, from the repository root (needs ``pip install triceratops``; run
``tls_search.py`` first)::

    python scripts/g249_11/triceratops_run.py 10 | tee results/g249-11/triceratops/triceratops.txt

Writes ``results/g249-11/triceratops/stars.csv`` (the stars searched and the depth each
would need), ``probabilities.csv`` (the scenario probabilities of every run),
``fpp_nfpp.json``, and TRICERATOPS's Gaia field population,
``417732194_gaia_background.csv``.
"""

import contextlib
import io
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import tess_data
import triceratops.triceratops as tr

warnings.filterwarnings("ignore")
RESULTS = Path(__file__).resolve().parents[2] / "results" / "g249-11"
OUT = RESULTS / "triceratops"
HALF_WINDOW_DAYS = 3.0 / 24
BIN_DAYS = 5.0 / 1440


def folded_binned(period, t0):
    """Days from mid-transit, flux and its uncertainty, in BIN_DAYS bins."""
    t, _, flux, _ = tess_data.joined(tess_data.load(tess_data.SPOC_SECTORS))
    phase = (((t - t0) / period + 0.5) % 1.0 - 0.5) * period
    edges = np.arange(-HALF_WINDOW_DAYS, HALF_WINDOW_DAYS + BIN_DAYS / 2, BIN_DAYS)
    index = np.digitize(phase, edges) - 1
    centers, means, errors = [], [], []
    for i in range(edges.size - 1):
        f = flux[index == i]
        if f.size > 1:
            centers.append(0.5 * (edges[i] + edges[i + 1]))
            means.append(f.mean())
            errors.append(f.std(ddof=1) / np.sqrt(f.size))
    return np.array(centers), np.array(means), float(np.median(errors))


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    OUT.mkdir(parents=True, exist_ok=True)
    tls = json.loads((RESULTS / "tls" / "2min.json").read_text())
    period, t0, depth = tls["period"], tls["T0_btjd"], tls["depth_fit_ppm"] * 1e-6
    time, flux, flux_err = folded_binned(period, t0)
    print(
        f"TLS ephemeris (sectors 19, 59, 60): P {period:.5f} d, T0 BTJD {t0:.4f}, "
        f"fitted depth {depth * 1e6:.0f} ppm"
    )
    print(
        f"folded light curve: {time.size} bins of {BIN_DAYS * 1440:.0f} min within "
        f"{HALF_WINDOW_DAYS * 24:.0f} h of mid-transit, uncertainty {flux_err * 1e6:.0f} ppm"
    )

    # TRICERATOPS writes the Gaia field population to the working directory and reads it
    # back later by its relative name
    with contextlib.chdir(OUT), contextlib.redirect_stdout(io.StringIO()):
        target = tr.target(ID=tess_data.TIC, sectors=np.array(tess_data.SPOC_SECTORS))
        apertures = target.get_spoc_apertures()
        target.calc_depths(tdepth=depth, all_ap_pixels=apertures)
    target.trilegal_fname = str(OUT / target.trilegal_fname)
    stars = target.stars
    stars.to_csv(OUT / "stars.csv", index=False)
    possible = stars[stars["tdepth"] > 0]
    print(f"\n{len(stars)} TIC stars within 10 pixels; {len(possible)} could produce the dip:")
    for _, s in possible.iterrows():
        print(
            f"  TIC {s['ID']:>10}  Tmag {s['Tmag']:5.2f}  {s['sep (arcsec)']:6.1f} arcsec  "
            f"flux ratio in aperture {s['fluxratio']:.4f}  needs a depth of {s['tdepth']:.4f}"
        )

    fpp, nfpp, tables = [], [], []
    for run in range(runs):
        target.calc_probs(
            time=time,
            flux_0=flux,
            flux_err_0=flux_err,
            P_orb=period,
            exptime=BIN_DAYS,
            parallel=True,
            verbose=0,
        )
        fpp.append(float(target.FPP))
        nfpp.append(float(target.NFPP))
        tables.append(target.probs.assign(run=run))
        print(f"run {run + 1}: FPP {target.FPP:.4f}, NFPP {target.NFPP:.2e}")
    probs = pd.concat(tables)
    probs.to_csv(OUT / "probabilities.csv", index=False)
    # a nearby-star scenario has one row per star: sum them within a run, then average
    per_run = probs.groupby(["run", "scenario"], sort=False)["prob"].sum()
    mean_probs = per_run.groupby("scenario", sort=False).mean()
    print("\nmean probability of each scenario over the runs (all stars together):")
    for scenario, p in mean_probs.sort_values(ascending=False).items():
        print(f"  {scenario:<7} {p:.4f}")
    nearby = probs[probs["ID"] != tess_data.TIC]
    by_star = nearby.groupby(["run", "ID"])["prob"].sum().groupby("ID").mean()
    print("\nmean share of NFPP from each nearby star:")
    for tic, p in by_star.sort_values(ascending=False).items():
        print(f"  TIC {tic:>10} {p:.2e}")
    summary = {
        "runs": runs,
        "FPP_mean": float(np.mean(fpp)),
        "FPP_std": float(np.std(fpp)),
        "NFPP_mean": float(np.mean(nfpp)),
        "NFPP_std": float(np.std(nfpp)),
        "FPP": fpp,
        "NFPP": nfpp,
    }
    (OUT / "fpp_nfpp.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        f"\nFPP = {summary['FPP_mean']:.4f} ± {summary['FPP_std']:.4f}, "
        f"NFPP = {summary['NFPP_mean']:.2e} ± {summary['NFPP_std']:.2e} ({runs} runs)"
    )


if __name__ == "__main__":
    main()
