"""Download, clean, and cache TESS SPOC 2-minute PDCSAP light curves.

For one TIC target the steps are:

1. Query MAST (through lightkurve) for every SPOC light curve with a 120-s
   exposure time, i.e. all sectors in which the star had a 2-minute postage stamp.
2. For each sector keep the PDCSAP flux. PDC ("Presearch Data Conditioning")
   removes common-mode instrumental systematics and corrects for flux from
   neighbouring stars in the aperture (CROWDSAP) and for flux falling outside it
   (FLFRCSAP), so transit depths are directly comparable to physical depths.
3. Drop cadences with bad QUALITY flags or non-finite values and normalise each
   sector by its median flux (sectors have different absolute flux levels).
4. Remove outliers with an asymmetric, trend-relative sigma clip (see
   :func:`find_outliers` for why low outliers are not clipped by default).
5. Stitch the sectors and cache the cleaned result plus metadata to disk, so
   subsequent runs never touch the network.

Raw FITS files are additionally kept in lightkurve's download cache under
``<cache_dir>/mast`` so that re-cleaning with different settings is offline too.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import os
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from importlib import metadata as _metadata
from pathlib import Path
from typing import Any

import numpy as np

from .lightcurve import LightCurve
from .utils import robust_std, running_median

log = logging.getLogger(__name__)

#: Bump when the processed-cache format or cleaning semantics change.
CACHE_FORMAT_VERSION = 1

# TESS QUALITY bits, from the TESS Science Data Products Description Document
# (EXP-TESS-ARC-ICD-0014, Table 28); names follow lightkurve's TessQualityFlags.
QUALITY_FLAGS: dict[str, int] = {
    "AttitudeTweak": 1,
    "SafeMode": 2,
    "CoarsePoint": 4,
    "EarthPoint": 8,
    "Argabrightening": 16,
    "Desat": 32,  # reaction-wheel momentum dump
    "ApertureCosmic": 64,
    "ManualExclude": 128,
    "Discontinuity": 256,
    "ImpulsiveOutlier": 512,
    "CollateralCosmic": 1024,
    "Straylight": 2048,
    "Straylight2": 4096,
    "PlanetSearchExclude": 8192,
    "BadCalibrationExclude": 16384,
    "InsufficientTargets": 32768,
}
_Q = QUALITY_FLAGS
#: Cadences that are "definitely useless" (same definition as lightkurve's default).
DEFAULT_BITMASK = (
    _Q["AttitudeTweak"]
    | _Q["SafeMode"]
    | _Q["CoarsePoint"]
    | _Q["EarthPoint"]
    | _Q["Argabrightening"]
    | _Q["Desat"]
    | _Q["ManualExclude"]
    | _Q["ImpulsiveOutlier"]
    | _Q["BadCalibrationExclude"]
)
#: More conservative: additionally drops cosmic-ray and scattered-light flags.
HARD_BITMASK = (
    DEFAULT_BITMASK
    | _Q["ApertureCosmic"]
    | _Q["CollateralCosmic"]
    | _Q["Straylight"]
    | _Q["Straylight2"]
)
BITMASKS: dict[str, int] = {
    "none": 0,
    "default": DEFAULT_BITMASK,
    "hard": HARD_BITMASK,
    "hardest": 65535,
}

# FITS header keywords worth carrying along (target, stellar and PDC information).
_HEADER_KEYS = (
    "OBJECT",
    "TICID",
    "SECTOR",
    "CAMERA",
    "CCD",
    "RA_OBJ",
    "DEC_OBJ",
    "TESSMAG",
    "TEFF",
    "LOGG",
    "MH",
    "RADIUS",
    "CROWDSAP",
    "FLFRCSAP",
    "PDCMETHD",
    "CDPP0_5",
    "CDPP1_0",
    "CDPP2_0",
    "DATA_REL",
    "PROCVER",
)


class NoDataError(RuntimeError):
    """Raised when no usable 2-minute SPOC data exist for a target."""


@dataclass(frozen=True)
class CleaningConfig:
    """Settings for turning raw PDCSAP photometry into a clean light curve.

    Attributes
    ----------
    bitmask : name in :data:`BITMASKS` or an explicit integer QUALITY bitmask.
    sigma_upper : clip points more than this many robust sigma *above* the trend.
    sigma_lower : clip points this far *below* the trend; ``None`` disables it
        (the default, because transits are negative excursions).
    clip_window : running-median window (days) that defines the local trend
        used for clipping; it should be long compared with transit durations.
    max_iterations : maximum number of clipping passes.
    min_points : sectors with fewer surviving points are discarded.
    """

    bitmask: str | int = "default"
    sigma_upper: float = 4.0
    sigma_lower: float | None = None
    clip_window: float = 0.5
    max_iterations: int = 5
    min_points: int = 100


@dataclass
class SectorData:
    """Raw photometry of one sector as read from a SPOC light-curve file."""

    sector: int
    time: np.ndarray
    flux: np.ndarray
    flux_err: np.ndarray
    quality: np.ndarray
    header: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- cleaning
def resolve_bitmask(bitmask: str | int) -> int:
    """Translate a named bitmask (``"default"``, ``"hard"``, ...) into an integer."""
    if isinstance(bitmask, str):
        try:
            return BITMASKS[bitmask.lower()]
        except KeyError:
            raise ValueError(
                f"unknown bitmask {bitmask!r}; choose from {sorted(BITMASKS)}"
            ) from None
    return int(bitmask)


def find_outliers(
    time: np.ndarray,
    flux: np.ndarray,
    window: float = 0.5,
    sigma_upper: float = 4.0,
    sigma_lower: float | None = None,
    max_iterations: int = 5,
) -> np.ndarray:
    """Flag outliers relative to a running-median trend. Returns True for outliers.

    The trend is a running median of the currently unflagged points; residuals
    are compared with a MAD-based robust sigma, and the procedure is iterated
    until the flagged set stops changing.

    Clipping is asymmetric by default: only points far *above* the trend
    (cosmic rays, flares, scattered-light glints) are removed. A transit is a
    run of consecutive points far *below* the trend -- a 1 % deep hot-Jupiter
    transit sits ~30 sigma low in bright-star TESS data -- so a symmetric clip
    would silently delete the signal we are looking for. Low clipping can be
    enabled via ``sigma_lower`` for data known to contain isolated low glitches.
    """
    time = np.asarray(time, dtype=float)
    flux = np.asarray(flux, dtype=float)
    outlier = np.zeros(time.size, dtype=bool)
    if time.size < 5:
        return outlier
    for _ in range(max_iterations):
        keep = ~outlier
        trend_keep = running_median(time[keep], flux[keep], window)
        trend = np.interp(time, time[keep], trend_keep)
        resid = flux - trend
        sigma = robust_std(resid[keep])
        if not np.isfinite(sigma) or sigma == 0:
            break
        new = resid > sigma_upper * sigma
        if sigma_lower is not None:
            new |= resid < -sigma_lower * sigma
        if np.array_equal(new, outlier):
            break
        outlier = new
    return outlier


def clean_sector(
    raw: SectorData, config: CleaningConfig | None = None
) -> tuple[LightCurve | None, dict[str, Any]]:
    """Quality-mask, normalise, and sigma-clip one sector.

    Returns the cleaned light curve (``None`` if too few points survive) and a
    dictionary of bookkeeping statistics describing what was removed and why.
    """
    config = config or CleaningConfig()
    bitmask = resolve_bitmask(config.bitmask)
    time = np.asarray(raw.time, dtype=float)
    flux = np.asarray(raw.flux, dtype=float)
    flux_err = np.asarray(raw.flux_err, dtype=float)
    quality = np.asarray(raw.quality, dtype=np.int64)

    flagged = (quality & bitmask) != 0
    finite = np.isfinite(time) & np.isfinite(flux) & np.isfinite(flux_err) & (flux_err > 0)
    good = ~flagged & finite
    stats: dict[str, Any] = {
        "sector": int(raw.sector),
        "n_raw": int(time.size),
        "n_quality_flagged": int(np.count_nonzero(flagged)),
        "n_nonfinite": int(np.count_nonzero(~finite & ~flagged)),
    }

    time, flux, flux_err = time[good], flux[good], flux_err[good]
    order = np.argsort(time)
    time, flux, flux_err = time[order], flux[order], flux_err[order]
    median = float(np.median(flux)) if flux.size else float("nan")
    stats["median_flux"] = median
    if flux.size < config.min_points or not np.isfinite(median) or median <= 0:
        stats.update(n_outliers=0, n_final=0, rejected=True)
        return None, stats
    flux = flux / median
    flux_err = flux_err / median

    outliers = find_outliers(
        time,
        flux,
        window=config.clip_window,
        sigma_upper=config.sigma_upper,
        sigma_lower=config.sigma_lower,
        max_iterations=config.max_iterations,
    )
    keep = ~outliers
    stats["n_outliers"] = int(np.count_nonzero(outliers))
    stats["n_final"] = int(np.count_nonzero(keep))
    if stats["n_final"] < config.min_points:
        stats["rejected"] = True
        return None, stats
    stats["rejected"] = False
    stats["rms_ppm"] = float(robust_std(flux[keep]) * 1e6)
    lc = LightCurve(
        time[keep],
        flux[keep],
        flux_err[keep],
        np.full(stats["n_final"], int(raw.sector)),
        {"sector_header": raw.header},
    )
    return lc, stats


def stitch(lightcurves: Sequence[LightCurve]) -> LightCurve:
    """Concatenate (already normalised) light curves and sort them in time."""
    if not lightcurves:
        raise NoDataError("nothing to stitch")
    sector = None
    if all(lc.sector is not None for lc in lightcurves):
        sector = np.concatenate([lc.sector for lc in lightcurves])
    return LightCurve(
        np.concatenate([lc.time for lc in lightcurves]),
        np.concatenate([lc.flux for lc in lightcurves]),
        np.concatenate([lc.flux_err for lc in lightcurves]),
        sector,
        {},
    )


def stellar_params_from_headers(headers: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Collect TIC stellar parameters recorded in the SPOC FITS headers.

    SPOC copies Teff, log g, [M/H], and radius from the TIC into every light
    curve file. They carry no uncertainties, so :mod:`transit_hunter.catalog`
    prefers a direct TIC query and uses these only as a fallback.
    """
    keys = {
        "TEFF": "teff",
        "LOGG": "logg",
        "MH": "mh",
        "RADIUS": "radius",
        "TESSMAG": "tmag",
        "RA_OBJ": "ra",
        "DEC_OBJ": "dec",
    }
    out: dict[str, Any] = dict.fromkeys(keys.values())
    for header in headers:
        for fits_key, name in keys.items():
            value = header.get(fits_key)
            if out[name] is None and isinstance(value, int | float) and np.isfinite(value):
                out[name] = float(value)
    return out


def process_sectors(
    raw_sectors: Sequence[SectorData],
    config: CleaningConfig | None = None,
    tic_id: int | None = None,
) -> LightCurve:
    """Clean every sector and stitch them into one normalised light curve."""
    config = config or CleaningConfig()
    cleaned: list[LightCurve] = []
    stats: list[dict[str, Any]] = []
    headers: list[dict[str, Any]] = []
    for raw in sorted(raw_sectors, key=lambda s: s.sector):
        lc, st = clean_sector(raw, config)
        stats.append(st)
        headers.append(raw.header)
        if lc is None:
            log.warning("sector %s rejected (%d usable points)", raw.sector, st["n_final"])
        else:
            cleaned.append(lc)
    if not cleaned:
        raise NoDataError(f"no sector of TIC {tic_id} survived cleaning")
    lc = stitch(cleaned)
    lc.meta.update(
        {
            "tic_id": None if tic_id is None else int(tic_id),
            "sectors": lc.sectors,
            "flux_column": "pdcsap_flux",
            "cadence_seconds": 120,
            "cleaning": asdict(config),
            "bitmask_value": resolve_bitmask(config.bitmask),
            "sector_stats": stats,
            "stellar_header": stellar_params_from_headers(headers),
            "crowdsap": {
                int(h["SECTOR"]): h.get("CROWDSAP") for h in headers if h.get("SECTOR") is not None
            },
            "created_utc": _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds"),
            "versions": _package_versions(),
        }
    )
    return lc


# --------------------------------------------------------------------------- network
def _as_float_array(values: Any) -> np.ndarray:
    """Convert (possibly masked) astropy quantities / arrays to a float ndarray."""
    if hasattr(values, "filled"):
        try:
            values = values.filled(np.nan)
        except (TypeError, ValueError):
            pass
    if hasattr(values, "value"):
        values = values.value
    return np.asarray(values, dtype=float)


def _plain(value: Any) -> Any:
    """Header values as plain JSON-friendly Python scalars."""
    if isinstance(value, bool | int | str) or value is None:
        return value
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    return value if np.isfinite(value) else None


def download_spoc_sectors(
    tic_id: int, download_dir: str | Path, sectors: Sequence[int] | None = None
) -> list[SectorData]:
    """Download every SPOC 120-s PDCSAP light curve of ``TIC tic_id`` from MAST.

    Requires network access to ``mast.stsci.edu``. All cadences are returned
    (``quality_bitmask="none"``); quality masking happens in :func:`clean_sector`
    so that it is explicit and testable.
    """
    import lightkurve as lk  # imported lazily: slow, and only needed for downloads

    target = f"TIC {int(tic_id)}"
    search = lk.search_lightcurve(
        target,
        mission="TESS",
        author="SPOC",
        exptime=120,
        sector=None if sectors is None else list(sectors),
    )
    if len(search) == 0:
        raise NoDataError(f"no SPOC 2-minute light curves found for {target}")
    log.info("found %d SPOC 2-min light curves for %s", len(search), target)
    collection = search.download_all(
        quality_bitmask="none", download_dir=str(download_dir), flux_column="pdcsap_flux"
    )
    if collection is None or len(collection) == 0:
        raise NoDataError(f"download failed for every sector of {target}")

    by_sector: dict[int, SectorData] = {}
    for lc in collection:
        header = {k: _plain(lc.meta.get(k)) for k in _HEADER_KEYS if k in lc.meta}
        if header.get("TICID") is not None and int(header["TICID"]) != int(tic_id):
            continue  # defensive: never mix in a neighbouring target
        sector = int(header.get("SECTOR", lc.meta.get("SECTOR")))
        quality = _as_float_array(lc.quality)
        # Masked QUALITY entries would otherwise cast to garbage integers.
        quality = np.where(np.isfinite(quality), quality, 0).astype(np.int64)
        item = SectorData(
            sector=sector,
            time=_as_float_array(lc.time.value),
            flux=_as_float_array(lc.flux),
            flux_err=_as_float_array(lc.flux_err),
            quality=quality,
            header=header,
        )
        # A sector can occasionally appear twice (reprocessed data releases):
        # keep the version with more finite samples.
        previous = by_sector.get(sector)
        if previous is None or np.isfinite(item.flux).sum() > np.isfinite(previous.flux).sum():
            by_sector[sector] = item
    if not by_sector:
        raise NoDataError(f"no light curves of {target} matched the requested TIC ID")
    return [by_sector[s] for s in sorted(by_sector)]


# --------------------------------------------------------------------------- caching
def default_cache_dir() -> Path:
    """Cache root: ``$TRANSIT_HUNTER_CACHE`` or ``~/.cache/transit_hunter``."""
    env = os.environ.get("TRANSIT_HUNTER_CACHE")
    return Path(env).expanduser() if env else Path("~/.cache/transit_hunter").expanduser()


def cache_path(
    tic_id: int,
    cache_dir: str | Path | None = None,
    config: CleaningConfig | None = None,
    sectors: Sequence[int] | None = None,
) -> Path:
    """Location of the processed light curve for this target and configuration."""
    config = config or CleaningConfig()
    key_source = json.dumps(
        {
            "format": CACHE_FORMAT_VERSION,
            "cleaning": asdict(config),
            "sectors": "all" if sectors is None else sorted(int(s) for s in sectors),
        },
        sort_keys=True,
    )
    key = hashlib.sha1(key_source.encode()).hexdigest()[:10]
    root = Path(cache_dir) if cache_dir is not None else default_cache_dir()
    return root / f"tic{int(tic_id)}" / f"spoc120_{key}.npz"


Downloader = Callable[[int, Path, Sequence[int] | None], list[SectorData]]


def fetch_lightcurve(
    tic_id: int,
    *,
    cache_dir: str | Path | None = None,
    sectors: Sequence[int] | None = None,
    config: CleaningConfig | None = None,
    force_download: bool = False,
    downloader: Downloader | None = None,
) -> LightCurve:
    """Return the cleaned, stitched 2-minute light curve of a TIC target.

    The processed light curve is cached as ``.npz``; later calls with the same
    cleaning configuration load it from disk. ``force_download=True`` bypasses
    the processed cache (e.g. to pick up newly released sectors). ``downloader``
    can be replaced for testing or for alternative data sources.
    """
    config = config or CleaningConfig()
    root = Path(cache_dir) if cache_dir is not None else default_cache_dir()
    path = cache_path(tic_id, root, config, sectors)
    if path.exists() and not force_download:
        lc = LightCurve.load(path)
        lc.meta["cache_file"] = str(path)
        lc.meta["loaded_from_cache"] = True
        return lc

    downloader = downloader or download_spoc_sectors
    raw = downloader(int(tic_id), root / "mast", sectors)
    lc = process_sectors(raw, config, tic_id=int(tic_id))
    lc.save(path)
    lc.meta["cache_file"] = str(path)
    lc.meta["loaded_from_cache"] = False
    return lc


def _package_versions() -> dict[str, str]:
    versions = {}
    for name in ("tess-transit-hunter", "numpy", "astropy", "lightkurve", "wotan"):
        try:
            versions[name] = _metadata.version(name)
        except _metadata.PackageNotFoundError:
            versions[name] = "not installed"
    return versions
