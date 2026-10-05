"""Is a batch candidate one periodic signal across every year TESS observed the star?

Usage, from the repository root::

    python scripts/check_other_years.py TIC PERIOD BATCH_SECTORS [options]

Options: ``--depth PPM`` (the batch's depth, to report the S/N it would give),
``--duration HOURS`` (centre the box durations on the batch's duration) and
``--window FRACTION`` (half-width of the period window, default 0.005).

BATCH_SECTORS is the batch's sector range, e.g. 27-39. The script assembles
  * the batch's own 2-minute sectors (where the candidate was found),
  * every other 2-minute sector of the star, earlier or later ("other years"),
  * full-frame-image light curves (TESS-SPOC, else QLP) for sectors without 2-minute data,
detrends each sector, and runs box least-squares searches over PERIOD ± window
(default 0.5 %): in the batch data alone (should find the candidate again), in
the other data alone, and in everything together. A real transit is coherent:
the other data show a dip of the same depth at the same period, and the joint
S/N grows. It also reports
  * the strongest short periodicity (0.05-0.6 d) of the batch data, and whether the
    candidate's period is a multiple of it (a sinusoid's troughs folded at n times
    its period look like a transit), and
  * the strongest periodicity of the raw flux in each sector (rotation check).
"""

import sys
import time
import warnings

import lightkurve as lk
import numpy as np
from astropy.timeseries import BoxLeastSquares, LombScargle

from transit_hunter.data import fetch_lightcurve
from transit_hunter.detrend import DetrendConfig, detrend
from transit_hunter.lightcurve import LightCurve

warnings.filterwarnings("ignore")
args = [a for a in sys.argv[1:] if not a.startswith("--")]
tic, period = int(args[0]), float(args[1])
lo, hi = (int(x) for x in args[2].split("-"))
batch_range = range(lo, hi + 1)
window = float(sys.argv[sys.argv.index("--window") + 1]) if "--window" in sys.argv else 0.005
depth_ppm = float(sys.argv[sys.argv.index("--depth") + 1]) if "--depth" in sys.argv else None
# the batch's transit duration (hours): the search grid is centred on it
dur_h = float(sys.argv[sys.argv.index("--duration") + 1]) if "--duration" in sys.argv else None
DETREND = DetrendConfig(window_length=0.75)
YEAR_STARTS = [1, 14, 27, 40, 56, 70, 84, 97, 110]  # first sector of each TESS year


def retry(fn, *a, tries=4, **k):
    """MAST sometimes answers 404 or drops the connection: try again after a pause."""
    for attempt in range(tries):
        try:
            return fn(*a, **k)
        except Exception as exc:  # network errors of every kind
            if attempt == tries - 1:
                raise
            print(f"  (retrying after {type(exc).__name__}: {str(exc)[:80]})", flush=True)
            time.sleep(15 * (attempt + 1))
    return None


def concat(parts: list[LightCurve]) -> LightCurve:
    return LightCurve(
        np.concatenate([p.time for p in parts]),
        np.concatenate([p.flux for p in parts]),
        np.concatenate([p.flux_err for p in parts]),
        np.concatenate([p.sector for p in parts]),
    )


def clipped(lc: LightCurve, nsigma: float = 6.0) -> LightCurve:
    """Drop points far from the detrended level either way (instrumental jumps)."""
    f = lc.flux
    sigma = 1.4826 * np.nanmedian(np.abs(f - np.nanmedian(f)))
    return lc.select(np.isfinite(f) & (np.abs(f - np.nanmedian(f)) < nsigma * sigma))


def fetch_many(sectors: list[int]) -> LightCurve | None:
    """The pipeline's cleaned 2-minute light curve of these sectors, skipping any that fail."""
    if not sectors:
        return None
    try:
        return retry(fetch_lightcurve, tic, sectors=sectors)
    except Exception as exc:
        print(f"  2-min sectors {sectors} together failed ({type(exc).__name__}); one by one")
    parts = []
    for s in sectors:
        try:
            parts.append(retry(fetch_lightcurve, tic, sectors=[s], tries=2))
        except Exception as exc:
            print(f"  2-min sector {s}: {type(exc).__name__}: {str(exc)[:80]}")
    return concat(parts) if parts else None


def year_of(sector: int) -> int:
    return int(np.searchsorted(YEAR_STARTS, int(sector), side="right"))


# ---------------------------------------------------------------- data
spoc = retry(lk.search_lightcurve, f"TIC {tic}", mission="TESS", author="SPOC", exptime=120)
two_min = sorted({int(m) for m in spoc.table["sequence_number"]}) if len(spoc) else []
batch = [s for s in two_min if s in batch_range]
other = [s for s in two_min if s not in batch_range]
raw_batch = fetch_many(batch)
if raw_batch is None:
    raise SystemExit(f"TIC {tic}: no batch data")
parts = {"batch (2-min)": [detrend(raw_batch, DETREND).flat]}
raws = [raw_batch]
raw_other = fetch_many(other)
if raw_other is not None:
    raws.append(raw_other)
    parts["other years (2-min)"] = [clipped(detrend(raw_other, DETREND).flat)]
covered = set(two_min)
ffi_sectors: dict[str, list[int]] = {}
for author in ("TESS-SPOC", "QLP"):
    try:
        found = retry(lk.search_lightcurve, f"TIC {tic}", mission="TESS", author=author)
    except Exception as exc:
        print(f"  {author} search failed: {exc}")
        continue
    for i in range(len(found)):
        sector = int(found.table["sequence_number"][i])
        if sector in covered:
            continue
        try:
            lc = retry(found[i].download, quality_bitmask="default", tries=2)
        except Exception as exc:  # one bad file must not stop the rest
            print(f"  {author} sector {sector}: {type(exc).__name__}")
            continue
        column = "pdcsap_flux" if author == "TESS-SPOC" else "kspsap_flux"
        if column not in lc.colnames:
            column = "sap_flux"
        t = np.asarray(lc.time.value, float)
        f = np.asarray(getattr(lc[column], "value", lc[column]), float)
        ok = np.isfinite(t) & np.isfinite(f) & (f > 0)
        if ok.sum() < 100:
            continue
        t, f = t[ok], f[ok] / np.median(f[ok])
        covered.add(sector)
        ffi_sectors.setdefault(author, []).append(sector)
        one = LightCurve(t, f, np.full(t.size, np.std(f)), np.full(t.size, sector))
        raws.append(one)
        parts.setdefault(f"other years (FFI, {author})", []).append(
            clipped(detrend(one, DETREND).flat)
        )
print(f"TIC {tic}: candidate P = {period} d, found in sectors {lo}-{hi}")
print(
    f"  2-min: batch {batch}, other {other}; FFI: "
    + ("; ".join(f"{a} {sorted(s)}" for a, s in ffi_sectors.items()) or "none")
)
data = {k: concat(v) for k, v in parts.items()}


def bls(lc: LightCurve, label: str):
    t, f, sec = lc.time, lc.flux, lc.sector
    dy = np.zeros(t.size)
    for s in np.unique(sec):
        m = sec == s
        dy[m] = 1.4826 * np.median(np.abs(f[m] - np.median(f[m])))
    baseline = t[-1] - t[0]
    if dur_h:
        durations = np.clip(dur_h / 24 * np.array([0.6, 0.8, 1.0, 1.3, 1.7]), 0.01, 0.4 * period)
    else:
        central = 13.0 / 24 * (period / 365.25) ** (1 / 3) * 0.6 ** (1 / 3)
        durations = np.clip(central * np.array([0.5, 0.7, 1.0, 1.4]), 0.02, 0.4 * period)
    df = durations.min() / (3 * baseline * period)
    freqs = np.arange(1 / (period * (1 + window)), 1 / (period * (1 - window)), df)
    res = BoxLeastSquares(t, f, dy=dy).power(1 / freqs, durations, objective="snr")
    i = int(np.argmax(res.depth_snr))
    p, d, t0 = res.period[i], res.duration[i], res.transit_time[i]
    phase = ((t - t0 + 0.5 * p) % p) - 0.5 * p
    inside = np.abs(phase) < d / 2
    n_tr = len(np.unique(np.round((t[inside] - t0) / p)))
    expected = (
        f"; {depth_ppm:.0f} ppm would give S/N "
        f"{depth_ppm * 1e-6 / np.median(dy) * np.sqrt(inside.sum()):.1f}"
        if depth_ppm
        else ""
    )
    print(
        f"  {label:28s} best P {p:.6f} ({(p / period - 1) * 100:+.3f} %), T14 {d * 24:.1f} h, "
        f"depth {res.depth[i] * 1e6:6.0f} ± {res.depth_err[i] * 1e6:4.0f} ppm, "
        f"S/N {res.depth_snr[i]:5.1f}, {n_tr} transits{expected}"
    )
    return p, d, t0, res


def depth_at(lc: LightCurve, p: float, d: float, t0: float) -> tuple[float, float, int]:
    phase = ((lc.time - t0 + 0.5 * p) % p) - 0.5 * p
    inside = np.abs(phase) < d / 2
    out = (np.abs(phase) > d) & (np.abs(phase) < 4 * d)
    if inside.sum() < 5 or out.sum() < 10:
        return float("nan"), float("nan"), 0
    sig = 1.4826 * np.median(np.abs(lc.flux[out] - np.median(lc.flux[out])))
    dep = np.mean(lc.flux[out]) - np.mean(lc.flux[inside])
    n = len(np.unique(np.round((lc.time[inside] - t0) / p)))
    return dep, sig * np.sqrt(1 / inside.sum() + 1 / out.sum()), n


# ---------------------------------------------------------------- searches
batch_lc = data["batch (2-min)"]
bls(batch_lc, "batch alone:")
others = [v for k, v in data.items() if k != "batch (2-min)"]
if others:
    bls(concat(others), "other years alone:")
everything = concat(list(data.values()))
P, D, T0, res = bls(everything, "all data together:")
baseline = everything.time[-1] - everything.time[0]
order = np.argsort(res.depth_snr)[::-1]
alt = [j for j in order if abs(res.period[j] - P) > 2 * D * P / baseline][:3]
print(
    "    next-best peaks at other periods: "
    + ", ".join(f"P {res.period[j]:.6f} S/N {res.depth_snr[j]:.1f}" for j in alt)
)
for name, lc in data.items():
    d, e, n = depth_at(lc, P, D, T0)
    print(
        f"    at that ephemeris, {name:28s}: {d * 1e6:6.0f} ± {e * 1e6:4.0f} ppm "
        f"({d / e:5.1f} σ), {n} transits"
    )
row = []
for y in sorted({year_of(s) for s in np.unique(everything.sector)}):
    sel = np.array([year_of(s) == y for s in everything.sector])
    d, e, n = depth_at(everything.select(sel), P, D, T0)
    row.append(f"year {y}: {d * 1e6:.0f}±{e * 1e6:.0f}")
print("    by year: " + ", ".join(row))

# ---------------------------------------------------------------- short-period variation
for name, lc in [("batch", batch_lc)] + ([("other years", concat(others))] if others else []):
    ls = LombScargle(lc.time, lc.flux)
    freq, power = ls.autopower(
        minimum_frequency=1 / 0.6, maximum_frequency=1 / 0.05, samples_per_peak=10
    )
    k = int(np.argmax(power))
    ps = 1 / freq[k]
    fap = ls.false_alarm_probability(power[k])
    model = ls.model(np.linspace(0, ps, 100) + lc.time[0], freq[k])
    ratio = period / ps
    flag = (
        "  <-- the candidate is a multiple of it"
        if fap < 1e-6 and round(ratio) >= 2 and abs(ratio - round(ratio)) < 0.02
        else ""
    )
    print(
        f"  strongest 0.05-0.6 d periodicity ({name}): {ps:.5f} d, semi-amplitude "
        f"{(model.max() - model.min()) / 2 * 1e6:.0f} ppm, false-alarm probability {fap:.1e}; "
        f"P / that = {ratio:.3f}{flag}"
    )

# ---------------------------------------------------------------- rotation
rot = []
near = 0
for raw in raws:
    for s in np.unique(raw.sector):
        m = raw.sector == s
        tt, ff = raw.time[m], raw.flux[m]
        if tt.size < 200:
            continue
        freq, power = LombScargle(tt, ff).autopower(minimum_frequency=1 / 15, maximum_frequency=10)
        k = int(np.argmax(power))
        prot = 1 / freq[k]
        if power[k] > 0.05 and any(abs(period / (prot * r) - 1) < 0.05 for r in (0.5, 1, 2)):
            near += 1
        rot.append(f"{s}: {prot:.2f} d ({power[k]:.2f})")
print(
    f"  raw-flux periodicity matches P, 2P or P/2 (power > 0.05) in {near} of {len(rot)} sectors; "
    + "; ".join(rot[:14])
    + (" ..." if len(rot) > 14 else "")
)
