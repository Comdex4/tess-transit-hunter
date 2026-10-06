"""Derived quantities and predicted transit times in the G 249-11 note (Tables 2 and 4).

From the TIC stellar parameters and the 2-minute fit stored in
``results/g249-11/s19-59-60/report.json``: the semi-major axis from Kepler's third law,
a/R*, the insolation, the equilibrium temperature (zero albedo, full heat redistribution),
radial-velocity semi-amplitudes, the duration of a transit at a few impact parameters, and
the mid-transit times of epochs 264-273 in BJD_TDB and geocentric UTC.

Usage, from the repository root::

    python scripts/g249_11/derived_values.py | tee results/g249-11/derived_values.txt
"""

import json
import math
from pathlib import Path

import astropy.units as u
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time

OUT = Path(__file__).resolve().parents[2] / "results" / "g249-11"
report = json.loads((OUT / "s19-59-60" / "report.json").read_text())
star = report["stellar"]
post = report["planets"][0]["fit"]["posterior"]
R, M, T = star["radius"], star["mass"], star["teff"]
P = post["period"]["median"]
P_ERR = max(post["period"]["err_lo"], post["period"]["err_hi"])
T0 = post["t0"]["median"] + 2457000.0
T0_ERR = max(post["t0"]["err_lo"], post["t0"]["err_hi"])
K_RATIO = post["rp_rs"]["median"]
T14_HOURS = post["t14_hours"]["median"]
# Gaia DR3 position of G 249-11 (epoch 2016.0); used only for the light-travel time
STAR = SkyCoord(82.67024641135 * u.deg, 68.90107712445 * u.deg)

a_au = (M * (P / 365.25) ** 2) ** (1 / 3)
a_rs = a_au * 215.032 / R
lum = R**2 * (T / 5772.0) ** 4
insolation = lum / a_au**2
teq = T * math.sqrt(1 / (2 * a_rs))
print(f"T0 = BJD_TDB {T0:.5f} ± {T0_ERR:.5f}, P = {P:.6f} ± {P_ERR:.6f} d")
print(
    f"a = {a_au:.4f} AU, a/R* = {a_rs:.2f}, L = {lum:.5f} L_sun, "
    f"S = {insolation:.2f} S_earth, Teq = {teq:.0f} K"
)
for mass in (2.5, 4.0, 6.0):
    semi_amplitude = 28.4329 * (mass * 0.0031463) * M ** (-2 / 3) * (P / 365.25) ** (-1 / 3)
    print(f"K for {mass} Earth masses: {semi_amplitude:.2f} m/s")
for b in (0.0, 0.5, 0.8):
    inc = math.acos(b / a_rs)
    chord = math.sqrt((1 + K_RATIO) ** 2 - b**2) / (a_rs * math.sin(inc))
    print(f"T14 for b = {b} at the catalog a/R*: {P / math.pi * math.asin(chord) * 24:.2f} h")
half_chord = math.sin(math.pi * T14_HOURS / (P * 24)) * a_rs
print(
    f"the fitted T14 of {T14_HOURS:.2f} h at the catalog a/R* means "
    f"b = {math.sqrt((1 + K_RATIO) ** 2 - half_chord**2):.2f}"
)

geocentre = EarthLocation.from_geocentric(0, 0, 0, unit=u.m)
print("epoch  BJD_TDB        1-sigma   UTC (geocentric)")
for n in range(264, 274):
    bjd = T0 + n * P
    barycentric = Time(bjd, format="jd", scale="tdb")
    geocentric = barycentric
    for _ in range(3):  # invert t_bary = t_geo + light-travel time(t_geo)
        geocentric = barycentric - geocentric.light_travel_time(STAR, location=geocentre)
    err_min = math.hypot(T0_ERR, n * P_ERR) * 1440
    print(f"{n:5d}  {bjd:.4f}  ±{err_min:4.1f} min  {geocentric.utc.strftime('%Y %b %d %H:%M')}")
