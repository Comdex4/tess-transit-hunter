"""Vet the TLS signal of G 249-11 (TIC 417732194) with LEO-Vetter.

LEO-Vetter (Kunimoto et al. 2025, AJ 170, 280) computes flux-level metrics for a transit
signal and checks them against pass-fail thresholds: 13 tests against noise and
systematic false alarms (FA) and 4 against astrophysical false positives (FP). This
script runs them, with the package's default thresholds (those of the paper), on two
sets of the light curves prepared by ``tess_data.py``, each at its own TLS period and
epoch from ``tls_search.py``:

  2min  sectors 19, 59 and 60 (13 transits at 2-minute cadence)
  all   all five sectors (2-minute and QLP 200-second data)

and prints every test with the metrics it uses and whether it passed. The starting
transit duration is that of the transit fit to the 2-minute data
(``s19-59-60/report.json``, 0.86 h); LEO-Vetter then fits its own trapezoid and transit
models. Stellar parameters are those of TIC 8, with LEO-Vetter's own limb-darkening
coefficients (Claret 2017).

LEO-Vetter's pixel-level test (the centroid offset of the difference image) needs the
``transit-diffImage`` package, which is installed from GitHub
(https://github.com/stevepur/transit-diffImage) rather than PyPI, and ``tess-point``.
With both installed, ``--pixel`` adds it for the five sectors.

Usage, from the repository root (needs ``pip install leo-vetter``; run
``tls_search.py`` first)::

    python scripts/g249_11/leo_vetter_run.py | tee results/g249-11/leo_vetter/leo_vetter.txt

Writes ``results/g249-11/leo_vetter/<set>_metrics.csv`` and LEO-Vetter's summary plot
``<set>_summary.png``.
"""

import json
import sys
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import tess_data
from leo_vetter import __version__ as leo_version
from leo_vetter import plots
from leo_vetter import thresholds as th
from leo_vetter.main import TCELightCurve
from leo_vetter.stellar import quadratic_ldc

warnings.filterwarnings("ignore")
matplotlib.use("Agg")
RESULTS = Path(__file__).resolve().parents[2] / "results" / "g249-11"
OUT = RESULTS / "leo_vetter"
SETS = {"2min": (19, 59, 60), "all": (19, 59, 60, 73, 86)}
SOLAR_DENSITY_CGS = 1.408
T = th._default_thresholds

FA_TESTS = (
    th.weak,
    th.invalid_transits,
    th.bad_shape,
    th.non_unique,
    th.chases,
    th.dmm,
    th.single_event,
    th.bad_fit,
    th.sinusoidal,
    th.unphysical_duration,
    th.asymmetric,
    th.chi,
    th.data_gapped,
)
FP_TESTS = (th.odd_even, th.vshaped, th.large, th.secondary)


def shown(m):
    """{test name: the metrics it uses, with its thresholds}."""
    ms1 = m["sig_pri"] / m["Fred"] - m["FA1"]
    ms2 = m["sig_pri"] - m["sig_ter"] - m["FA2"]
    ms3 = m["sig_pri"] - m["sig_pos"] - m["FA2"]
    ms4 = m["sig_sec"] / m["Fred"] - m["FA1"]
    ms5 = m["sig_sec"] - m["sig_ter"] - m["FA2"]
    ms6 = m["sig_sec"] - m["sig_pos"] - m["FA2"]
    asym = abs(m["trap_qtran_left"] - m["trap_qtran_right"]) / np.hypot(
        m["trap_qtran_err_left"], m["trap_qtran_err_right"]
    )
    return {
        "weak": f"MES {m['MES']:.1f} (fails below {T['MES']})",
        "invalid_transits": (
            f"after dropping bad transits: MES {m['new_MES']:.1f}, "
            f"{m['new_N_transit']} transits (fails below {T['MES']} or {T['N_transit']})"
        ),
        "bad_shape": f"SHP {m['SHP']:.2f} (fails above {T['SHP']})",
        "non_unique": (
            f"MS1 {ms1:.1f}, MS2 {ms2:.1f}, MS3 {ms3:.1f} "
            f"(fail below {T['MS1']}, {T['MS2']}, {T['MS3']})"
        ),
        "chases": (
            f"mean chases {m['mean_chases']:.2f} (fails below {T['chases']}, "
            f"applied only with 5 transits or fewer; here {m['N_transit']})"
        ),
        "dmm": f"mean/median depth {m['DMM']:.2f} (fails above {T['DMM']})",
        "single_event": (
            f"max SES / MES {m['max_SES'] / m['MES']:.2f} (fails above "
            f"{T['max_SES_to_MES']}, applied only with 10 transits or fewer)"
        ),
        "bad_fit": (
            f"AIC(transit) - AIC(line) {m['transit_aic'] - m['line_aic']:.0f} "
            f"(fails above {T['AIC1']} with 10 transits or fewer, {T['AIC2']} with more); "
            f"reduced chi2 {m['transit_chisqr']:.3f} vs line {m['line_chisqr']:.3f}"
        ),
        "sinusoidal": (f"SWEET sine significance {m['sine_sig']:.1f} (fails above {T['SWEET']})"),
        "unphysical_duration": (
            f"a/R* {m['transit_aRs']:.1f} (fit), {m['aRs']:.1f} (star); expected/fitted "
            f"duration {m['q'] / m['trap_qtran']:.2f} (fails below 0.6)"
        ),
        "asymmetric": f"ingress/egress asymmetry {asym:.1f} sigma (fails above {T['ASYM']})",
        "chi": f"CHI {m['CHI']:.1f} (fails below {T['CHI']})",
        "data_gapped": (
            f"{m['N_gap_2.0']} of {m['N_transit']} transits near gaps "
            f"(fails at a fraction of {T['frac_gap']} or more)"
        ),
        "odd_even": (
            f"odd/even depths differ by {m['sig_dep']:.1f} (box), "
            f"{m['trap_sig_dep']:.1f} (trapezoid), {m['transit_sig_dep']:.1f} sigma (transit); "
            f"epochs by {m['trap_sig_epo']:.1f}, {m['transit_sig_epo']:.1f} sigma"
        ),
        "vshaped": (
            f"b + Rp/R* = {m['transit_b'] + m['transit_RpRs']:.2f} (fails above {T['V_shape']})"
        ),
        "large": f"Rp {m['Rp']:.2f} Earth radii (fails above {T['size']})",
        "secondary": (
            f"secondary {m['dep_sec'] * 1e6:.0f} ppm, significance {m['sig_sec']:.1f}; "
            f"MS4 {ms4:.1f}, MS5 {ms5:.1f}, MS6 {ms6:.1f}"
        ),
        "offset": (
            f"difference-image offset {m.get('offset_qual', np.nan):.1f} arcsec "
            f"(fails above {T['offset']})"
        ),
    }


def vet(name, sectors, star, duration_days, pixel):
    tls = json.loads((RESULTS / "tls" / f"{name}.json").read_text())
    t, raw, flux, err = tess_data.joined(sectors)
    per, epo, dur = tls["period"], tls["T0_btjd"], duration_days
    tlc = TCELightCurve(tess_data.TIC, t, raw, flux, err, per, epo, dur)
    tlc.compute_flux_metrics(star, verbose=False)
    tests = FA_TESTS + FP_TESTS
    if pixel:
        from leo_vetter.pixel import pixel_vetting

        pixel_vetting(tlc, star, list(sectors), tdi_dir=str(OUT / "pixel"))
        tests += (th.offset,)
    m = tlc.metrics
    print(f"\n== {name}: sectors {', '.join(map(str, sectors))} ({t.size} points)")
    print(
        f"   TLS ephemeris: P {per:.5f} d, T0 BTJD {epo:.4f}; "
        f"duration of the transit fit {dur * 24:.2f} h"
    )
    print(
        f"   LEO-Vetter: {m['N_transit']} transits, depth {m['dep'] * 1e6:.0f} ppm, "
        f"MES {m['MES']:.1f}; transit fit P {m['transit_per']:.5f} d, "
        f"Rp/R* {m['transit_RpRs']:.4f}, b {m['transit_b']:.2f}, "
        f"a/R* {m['transit_aRs']:.1f}, Rp {m['Rp']:.2f} ± {m['Rp_err']:.2f} Earth radii"
    )
    text = shown(m)
    failed = []
    for test in tests:
        flag, message = test(m, T)
        outcome = "FAIL" if bool(flag) else "pass"
        if outcome == "FAIL":
            failed.append(message)
        kind = message.split(":")[0]
        print(f"   {outcome}  {kind} {test.__name__:<20} {text[test.__name__]}")
    fa = bool(th.check_thresholds(m, "FA"))
    fp = bool(th.check_thresholds(m, "FP"))
    verdict = "FA" if fa else "FP" if fp else "PC"
    print(f"   disposition: {verdict} ({len(failed)} of {len(tests)} tests failed)")
    tlc.save_metrics(OUT / f"{name}_metrics.csv")
    plots.plot_summary(tlc, star, save_fig=True, save_file=str(OUT / f"{name}_summary.png"))


def main():
    pixel = "--pixel" in sys.argv[1:]
    OUT.mkdir(parents=True, exist_ok=True)
    s = tess_data.STAR
    u1, u2 = quadratic_ldc(s["teff"], s["logg"])
    rho = s["density_solar"] * SOLAR_DENSITY_CGS
    star = {
        "tic": tess_data.TIC,
        "ra": s["ra"],
        "dec": s["dec"],
        "rad": s["radius"],
        "e_rad": s["radius_err"],
        "mass": s["mass"],
        "e_mass": s["mass_err"],
        "Teff": s["teff"],
        "e_Teff": s["teff_err"],
        "rho": rho,
        "u1": float(u1),
        "u2": float(u2),
    }
    print(
        f"LEO-Vetter {leo_version}; TIC {tess_data.TIC}: R* {s['radius']:.3f}, M* {s['mass']:.3f}, "
        f"Teff {s['teff']:.0f} K, density {rho:.1f} g/cm3, u1 {float(u1):.3f}, u2 {float(u2):.3f}"
    )
    fit = json.loads((RESULTS / "s19-59-60" / "report.json").read_text())["planets"][0]["fit"]
    duration_days = fit["posterior"]["t14_hours"]["median"] / 24
    data = tess_data.load(tess_data.SPOC_SECTORS + tess_data.QLP_SECTORS)
    for name, sectors in SETS.items():
        vet(name, {k: data[k] for k in sectors}, star, duration_days, pixel)


if __name__ == "__main__":
    main()
