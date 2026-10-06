"""Light curves of G 249-11 (TIC 417732194) for the analysis with published tools.

Shared by ``tls_search.py``, ``leo_vetter_run.py`` and ``triceratops_run.py``, so that all
three see the same data, prepared with public, published software only:

- SPOC 2-minute PDCSAP flux for sectors 19, 59 and 60, and QLP detrended flux from the
  200-second full-frame images for sectors 73 and 86, downloaded from MAST with
  Lightkurve (default quality mask; for QLP, only cadences with QUALITY = 0, which
  removes QLP's stray-light and low-precision cadences);
- each sector divided by its median and detrended with wotan's time-windowed biweight
  filter (Hippke et al. 2019, AJ 158, 143), with a 0.75-day window (about 20 transit
  durations);
- points more than 4 robust standard deviations above the detrended flux (flares)
  removed; points below it are kept, since a transit is a dip;
- each sector's uncertainties scaled so that their median equals the sector's robust
  scatter.

Not run on its own.
"""

from dataclasses import dataclass

import lightkurve as lk
import numpy as np
from wotan import flatten

TIC = 417732194
SPOC_SECTORS = (19, 59, 60)
QLP_SECTORS = (73, 86)
WINDOW_DAYS = 0.75
CLIP_SIGMA = 4.0
# TIC 8 (Stassun et al. 2019), the same values as the pipeline report
STAR = {
    "radius": 0.265811,
    "radius_err": 0.00804493,
    "mass": 0.238162,
    "mass_err": 0.0201736,
    "teff": 3180.0,
    "teff_err": 157.0,
    "logg": 4.96579,
    "density_solar": 12.681,
    "ra": 82.67024641135,  # Gaia DR3, epoch 2016.0
    "dec": 68.90107712445,
    "tmag": 12.2995,
}


@dataclass
class Sector:
    """One sector, normalized (``raw``) and detrended (``flux``), times in BTJD."""

    sector: int
    author: str
    exptime_s: float
    time: np.ndarray
    raw: np.ndarray
    flux: np.ndarray
    flux_err: np.ndarray


def robust_std(x):
    return 1.4826 * np.nanmedian(np.abs(x - np.nanmedian(x)))


def load_sector(sector):
    author = "SPOC" if sector in SPOC_SECTORS else "QLP"
    extra = {"exptime": 120} if author == "SPOC" else {}
    found = lk.search_lightcurve(
        f"TIC {TIC}", mission="TESS", author=author, sector=sector, **extra
    )
    if len(found) != 1:
        raise RuntimeError(f"expected one {author} light curve for sector {sector}: {found}")
    lc = found[0].download(quality_bitmask="default")
    # SPOC: PDCSAP. QLP: its detrended flux, called KSPSAP_FLUX in early releases and
    # DET_FLUX in later ones
    column = next(c for c in ("pdcsap_flux", "det_flux", "kspsap_flux") if c in lc.colnames)
    time = np.asarray(lc.time.value, float)
    flux = np.asarray(lc[column].value, float)
    err = np.asarray(lc[f"{column}_err"].value, float)
    ok = np.isfinite(time) & np.isfinite(flux) & np.isfinite(err) & (flux > 0) & (err > 0)
    if author == "QLP":
        # QLP sets flags of its own (stray light, low precision) that Lightkurve's
        # default mask keeps; as in QLP's own good-cadence files, keep QUALITY == 0 only
        ok &= np.asarray(lc.quality.value) == 0
    time, flux, err = time[ok], flux[ok], err[ok]
    median = np.median(flux)
    raw, err = flux / median, err / median
    detrended = flatten(
        time, raw, method="biweight", window_length=WINDOW_DAYS, break_tolerance=0.5
    )
    keep = np.isfinite(detrended)
    scatter = robust_std(detrended[keep])
    keep &= detrended - 1.0 < CLIP_SIGMA * scatter
    # The archive uncertainties do not match the scatter of every sector (those of QLP
    # are about 20 % too small), so each sector's are scaled to its robust scatter.
    err = err * scatter / np.median(err[keep])
    exptime = 120.0 if author == "SPOC" else 200.0
    return Sector(sector, author, exptime, time[keep], raw[keep], detrended[keep], err[keep])


def load(sectors):
    """{sector: Sector} for the requested sectors."""
    return {s: load_sector(s) for s in sectors}


def joined(sectors):
    """Time, normalized flux, detrended flux and error of several sectors, time-ordered."""
    parts = [sectors[s] for s in sorted(sectors)]
    arrays = [np.concatenate([getattr(p, k) for p in parts]) for k in ("time", "raw", "flux")]
    arrays.append(np.concatenate([p.flux_err for p in parts]))
    order = np.argsort(arrays[0])
    return tuple(a[order] for a in arrays)
