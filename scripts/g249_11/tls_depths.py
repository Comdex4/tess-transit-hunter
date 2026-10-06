"""Is each TLS peak of G 249-11 (TIC 417732194) the same dip in every sector?

A planet's transits have the same depth in every sector; a peak built from a few
unrelated dips does not. For the candidate (TLS ephemeris of the 2-minute data,
``tls/2min.json``) and for the highest peak of the search of the other years
(``tls/others.json``), this script measures a box depth at every epoch with data, in the
light curves of ``tess_data.py``: the mean of the points within half the fitted duration
(0.86 h) of mid-transit against the mean of those between one and four durations away.
It prints the weighted mean depth of each sector and the chi-square of those means
about their overall mean, with its probability of being exceeded if the depth were the
same in every sector.

Usage, from the repository root (run ``tls_search.py`` first)::

    python scripts/g249_11/tls_depths.py | tee results/g249-11/tls/tls_depths.txt
"""

import json
import warnings
from pathlib import Path

import numpy as np
import tess_data
from scipy.stats import chi2

warnings.filterwarnings("ignore")
RESULTS = Path(__file__).resolve().parents[2] / "results" / "g249-11"
MIN_IN, MIN_OUT = 8, 20


def sector_depths(data, period, t0, duration):
    """{sector: (depths of its epochs, their errors)} for a box of the given duration."""
    out = {}
    for s, x in data.items():
        epoch = np.round((x.time - t0) / period)
        dt = x.time - t0 - epoch * period
        depths, errors = [], []
        for e in np.unique(epoch):
            inside = (epoch == e) & (np.abs(dt) < duration / 2)
            around = (epoch == e) & (np.abs(dt) > duration) & (np.abs(dt) < 4 * duration)
            if inside.sum() >= MIN_IN and around.sum() >= MIN_OUT:
                depths.append(np.mean(x.flux[around]) - np.mean(x.flux[inside]))
                errors.append(np.std(x.flux[around]) / np.sqrt(inside.sum()))
        if depths:
            out[s] = (np.array(depths) * 1e6, np.array(errors) * 1e6)
    return out


def report(label, data, period, t0, duration):
    print(f"\n== {label}: P {period:.5f} d, T0 BTJD {t0:.4f}, box {duration * 24:.2f} h")
    means, sigmas = [], []
    for s, (d, e) in sector_depths(data, period, t0, duration).items():
        w = 1 / e**2
        mean, sigma = np.sum(w * d) / np.sum(w), 1 / np.sqrt(np.sum(w))
        means.append(mean)
        sigmas.append(sigma)
        epochs = ", ".join(f"{a:.0f}" for a in d)
        print(f"   sector {s}: {d.size} epochs ({epochs}); mean {mean:.0f} ± {sigma:.0f} ppm")
    means, sigmas = np.array(means), np.array(sigmas)
    w = 1 / sigmas**2
    overall = np.sum(w * means) / np.sum(w)
    statistic = np.sum((means - overall) ** 2 * w)
    dof = means.size - 1
    print(
        f"   all sectors: {overall:.0f} ± {1 / np.sqrt(np.sum(w)):.0f} ppm; chi2 of the "
        f"sector means {statistic:.1f} for {dof} degrees of freedom, "
        f"p = {chi2.sf(statistic, dof):.2g}"
    )


def main():
    report_json = json.loads((RESULTS / "s19-59-60" / "report.json").read_text())
    duration = report_json["planets"][0]["fit"]["posterior"]["t14_hours"]["median"] / 24
    data = tess_data.load(tess_data.SPOC_SECTORS + tess_data.QLP_SECTORS)
    for name, label in (("2min", "candidate"), ("others", "highest peak of the other years")):
        tls = json.loads((RESULTS / "tls" / f"{name}.json").read_text())
        report(f"{label} (tls/{name}.json)", data, tls["period"], tls["T0_btjd"], duration)


if __name__ == "__main__":
    main()
