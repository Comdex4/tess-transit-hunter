"""Target-pixel data for the centroid test.

The light curve says *whether* the light in the target's aperture dipped; the
target-pixel file (TPF), a small stamp of calibrated pixels around the star at
every 2-minute cadence, says *where* the light went missing. This module fetches
what :mod:`transit_hunter.centroid` needs:

- SPOC 2-minute TPFs from MAST, through lightkurve, kept in the same download
  cache as the light curves (``<cache_dir>/mast``);
- the TESS pixel response function (PRF), the image a point source leaves on the
  detector, from the MAST archive (cached under ``<cache_dir>/prf``);
- the stars around the target, from the TIC (not cached).

Network access is needed only the first time. Everything that interprets the
data is a pure function, tested offline with synthetic stamps and PRFs.
"""

from __future__ import annotations

import logging
import math
import re
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.interpolate import RectBivariateSpline
from scipy.special import ndtr

from .data import DEFAULT_BITMASK, default_cache_dir, download_with_cache_repair

log = logging.getLogger(__name__)

#: Plate scale of the TESS cameras, arcsec per pixel.
TESS_PIXEL_ARCSEC = 21.0
#: Epoch (Julian year) of the TIC coordinates.
TIC_EPOCH = 2000.0

PRF_URL = "https://archive.stsci.edu/missions/tess/models/prf_fitsfiles"
#: Samples per pixel in the PRF files.
PRF_SAMPLES = 9


@dataclass
class PixelData:
    """Calibrated pixels of one sector's target-pixel file (good cadences only)."""

    sector: int
    camera: int
    ccd: int
    column: int  # CCD column of the stamp's first pixel
    row: int  # CCD row of the stamp's first pixel
    time: np.ndarray  # BTJD
    flux: np.ndarray  # (n_cadences, n_rows, n_cols), electrons per second
    wcs: Any  # astropy.wcs.WCS of the stamp
    ra: float  # target position (deg) at the TIC epoch, J2000
    dec: float
    tmag: float | None
    aperture: np.ndarray  # SPOC photometric aperture, bool (n_rows, n_cols)
    pmra: float = 0.0  # proper motion (mas/yr; the RA component times cos dec)
    pmdec: float = 0.0

    @property
    def shape(self) -> tuple[int, int]:
        return int(self.flux.shape[1]), int(self.flux.shape[2])

    @property
    def epoch(self) -> float:
        """Julian year of the sector's middle cadence."""
        return btjd_to_year(float(np.median(self.time))) if self.time.size else TIC_EPOCH

    def target_radec(self) -> tuple[float, float]:
        """The target's position when the sector was observed (proper motion applied)."""
        return propagate(self.ra, self.dec, self.pmra, self.pmdec, self.epoch)

    def world_to_pixel(self, ra: float, dec: float) -> tuple[float, float]:
        """Stamp position (column, row; 0 = center of the first pixel) of a sky position."""
        x, y = self.wcs.world_to_pixel_values(ra, dec)
        return float(x), float(y)

    def target_pixel(self) -> tuple[float, float]:
        return self.world_to_pixel(*self.target_radec())

    def sky_offset(self, x: float, y: float) -> tuple[float, float]:
        """Offset (east, north) in arcsec of stamp position (x, y) from the target."""
        ra, dec = self.wcs.pixel_to_world_values(x, y)
        return sky_offset(*self.target_radec(), float(ra), float(dec))

    def sky_jacobian(self, x: float, y: float, step: float = 0.05) -> np.ndarray:
        """d(east, north)/d(column, row) in arcsec per pixel, at a stamp position."""
        e1, n1 = self.sky_offset(x + step, y)
        e0, n0 = self.sky_offset(x - step, y)
        e3, n3 = self.sky_offset(x, y + step)
        e2, n2 = self.sky_offset(x, y - step)
        return np.array([[e1 - e0, e3 - e2], [n1 - n0, n3 - n2]]) / (2 * step)


def btjd_to_year(btjd: float) -> float:
    """Julian year of a TESS time (BTJD = BJD - 2457000)."""
    return 2000.0 + (btjd + 2457000.0 - 2451545.0) / 365.25


def propagate(ra: float, dec: float, pmra: float, pmdec: float, year: float) -> tuple[float, float]:
    """Position at ``year`` of a star at (ra, dec) at the TIC epoch (linear motion).

    ``pmra`` is the proper motion in right ascension times cos(dec), and ``pmdec``
    the one in declination, both in mas/yr. Nearby stars move several arcsec
    between 2000 and the TESS observations, a sizable fraction of a pixel.
    """
    dt = year - TIC_EPOCH
    cos_dec = max(math.cos(math.radians(dec)), 1e-6)
    return (
        ra + pmra * dt / 3.6e6 / cos_dec,
        dec + pmdec * dt / 3.6e6,
    )


def sky_offset(ra0: float, dec0: float, ra: float, dec: float) -> tuple[float, float]:
    """Offset (east, north) in arcsec of (ra, dec) from (ra0, dec0); small-angle."""
    d_ra = (ra - ra0 + 180.0) % 360.0 - 180.0
    return (
        d_ra * math.cos(math.radians(dec0)) * 3600.0,
        (dec - dec0) * 3600.0,
    )


@dataclass
class Neighbour:
    """A TIC star near the target (position at the TIC epoch, J2000)."""

    tic_id: int
    ra: float
    dec: float
    tmag: float
    pmra: float = 0.0  # mas/yr, times cos(dec) for the RA component
    pmdec: float = 0.0

    def radec_at(self, year: float) -> tuple[float, float]:
        return propagate(self.ra, self.dec, self.pmra, self.pmdec, year)


# --------------------------------------------------------------------------- PRF
class PRFModel:
    """The TESS pixel response function at one place on the detector.

    The PRF files sample, on a 13 x 13 pixel grid at 1/9-pixel resolution, the
    fraction of a star's flux collected by a pixel whose center lies at a given
    offset from the star: sample (r, c) of the 117 x 117 array is the offset
    ((r - 58) / 9, (c - 58) / 9) pixels (rows, columns). A cubic spline through
    those samples gives the fraction at any offset, so a star at any sub-pixel
    position can be drawn into a stamp. MAST has five by five models per camera
    and CCD (one set for sectors 1-3, another from sector 4); the one at a
    target's position is interpolated bilinearly between the four around it, as
    in Keaton Bell's TESS_PRF (MIT license).
    """

    def __init__(self, image: np.ndarray, samples: int = PRF_SAMPLES):
        image = np.asarray(image, dtype=float)
        n = image.shape[0]
        offsets = (np.arange(n) - (n - 1) / 2) / samples
        self.image = image
        self.extent = float(offsets[-1])
        self._spline = RectBivariateSpline(offsets, offsets, image, kx=3, ky=3)

    def model(self, x0: float, y0: float, shape: tuple[int, int]) -> np.ndarray:
        """Fraction of a star's flux in each pixel of a stamp, star at (x0, y0) = (column, row)."""
        ny, nx = shape
        dy = np.arange(ny) - y0
        dx = np.arange(nx) - x0
        out = self._spline(dy, dx)
        out[np.abs(dy) > self.extent, :] = 0.0
        out[:, np.abs(dx) > self.extent] = 0.0
        return np.clip(out, 0.0, None)

    @classmethod
    def gaussian(cls, sigma: float = 0.8, half_width: int = 6) -> PRFModel:
        """A Gaussian point-spread function integrated over square pixels (for tests)."""
        n = (2 * half_width + 1) * PRF_SAMPLES
        off = (np.arange(n) - (n - 1) / 2) / PRF_SAMPLES
        frac = ndtr((off + 0.5) / sigma) - ndtr((off - 0.5) / sigma)
        return cls(np.outer(frac, frac))

    @classmethod
    def from_mast(
        cls,
        sector: int,
        camera: int,
        ccd: int,
        column: float,
        row: float,
        cache_dir: str | Path | None = None,
    ) -> PRFModel:
        """The PRF at CCD position (column, row), downloaded once from MAST."""
        from astropy.io import fits

        epoch = "start_s0001" if sector < 4 else "start_s0004"
        subdir = f"cam{int(camera)}_ccd{int(ccd)}"
        folder = Path(cache_dir or default_cache_dir()) / "prf" / epoch / subdir
        grid = _prf_grid(folder, f"{PRF_URL}/{epoch}/{subdir}/")
        rows = np.array(sorted({r for r, _ in grid}), dtype=float)
        cols = np.array(sorted({c for _, c in grid}), dtype=float)
        r = float(np.clip(row, rows[0], rows[-1]))
        c = float(np.clip(column, cols[0], cols[-1]))
        i = int(np.clip(np.searchsorted(rows, r) - 1, 0, len(rows) - 2))
        j = int(np.clip(np.searchsorted(cols, c) - 1, 0, len(cols) - 2))
        wr = (r - rows[i]) / (rows[i + 1] - rows[i])
        wc = (c - cols[j]) / (cols[j + 1] - cols[j])
        image = 0.0
        for rr, cc, weight in (
            (rows[i], cols[j], (1 - wr) * (1 - wc)),
            (rows[i], cols[j + 1], (1 - wr) * wc),
            (rows[i + 1], cols[j], wr * (1 - wc)),
            (rows[i + 1], cols[j + 1], wr * wc),
        ):
            if weight > 0:
                name = grid[(int(rr), int(cc))]
                path = folder / name
                if not path.exists():
                    _download(f"{PRF_URL}/{epoch}/{subdir}/{name}", path)
                image = image + weight * fits.getdata(path, 0).astype(float)
        return cls(np.asarray(image))


def _prf_grid(folder: Path, url: str) -> dict[tuple[int, int], str]:
    """{(row, column): file name} of the PRF models of one camera/CCD (listing cached)."""
    listing = folder / "listing.txt"
    if listing.exists():
        names = listing.read_text().split()
    else:
        with urllib.request.urlopen(url, timeout=60) as response:
            html = response.read().decode()
        names = sorted(set(re.findall(r'href="([^"/]*prf-\d-\d-row\d{4}-col\d{4}\.fits)"', html)))
        if not names:
            raise LookupError(f"no PRF files listed at {url}")
        folder.mkdir(parents=True, exist_ok=True)
        listing.write_text("\n".join(names) + "\n")
    grid = {}
    for name in names:
        m = re.search(r"row(\d{4})-col(\d{4})", name)
        if m:
            grid[(int(m.group(1)), int(m.group(2)))] = name
    return grid


def _download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    with urllib.request.urlopen(url, timeout=120) as response:
        tmp.write_bytes(response.read())
    tmp.replace(path)


# --------------------------------------------------------------------------- MAST
def pixel_data_from_tpf(tpf: Any, bitmask: int = DEFAULT_BITMASK) -> PixelData:
    """Good cadences of a lightkurve ``TessTargetPixelFile``."""
    time = np.asarray(tpf.time.value, dtype=float)
    flux = np.asarray(getattr(tpf.flux, "value", tpf.flux), dtype=np.float32)
    quality = np.asarray(tpf.quality).astype(np.int64)
    # a cadence is usable if most of its pixels are
    finite = np.isfinite(flux).mean(axis=(1, 2)) > 0.5
    good = ((quality & bitmask) == 0) & np.isfinite(time) & finite
    header = tpf.hdu[0].header
    tmag = header.get("TESSMAG")

    def motion(key: str) -> float:
        value = header.get(key)
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 0.0
        return value if np.isfinite(value) else 0.0

    return PixelData(
        sector=int(tpf.sector),
        camera=int(header["CAMERA"]),
        ccd=int(header["CCD"]),
        column=int(tpf.column),
        row=int(tpf.row),
        time=time[good],
        flux=flux[good],
        wcs=tpf.wcs,
        ra=float(tpf.ra),
        dec=float(tpf.dec),
        tmag=float(tmag) if tmag is not None and np.isfinite(float(tmag)) else None,
        aperture=np.asarray(tpf.pipeline_mask, dtype=bool),
        pmra=motion("PMRA"),
        pmdec=motion("PMDEC"),
    )


def download_tpf(tic_id: int, sector: int, download_dir: str | Path) -> PixelData:
    """The SPOC 2-minute target-pixel file of ``TIC tic_id`` in one sector (MAST)."""
    import lightkurve as lk  # imported lazily: slow, and only needed for downloads

    search = lk.search_targetpixelfile(
        f"TIC {int(tic_id)}", mission="TESS", author="SPOC", exptime=120, sector=int(sector)
    )
    if len(search) == 0:
        raise LookupError(f"no SPOC 2-minute target-pixel file of TIC {tic_id} in sector {sector}")
    tpf = download_with_cache_repair(
        lambda: search[0].download(download_dir=str(download_dir), quality_bitmask="none"),
        download_dir,
    )
    if tpf is None:
        raise LookupError(f"download of TIC {tic_id}'s sector {sector} pixels failed")
    header_tic = tpf.hdu[0].header.get("TICID")
    if header_tic is not None and int(header_tic) != int(tic_id):
        raise LookupError(f"sector {sector} pixel file belongs to TIC {header_tic}")
    return pixel_data_from_tpf(tpf)


def query_neighbours(ra: float, dec: float, radius_arcsec: float = 150.0) -> list[Neighbour]:
    """TIC stars within ``radius_arcsec`` of a position (MAST; requires network)."""
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from astroquery.mast import Catalogs

    table = Catalogs.query_region(
        SkyCoord(ra, dec, unit="deg"), radius=radius_arcsec * u.arcsec, catalog="TIC"
    )

    def number(row: Any, key: str) -> float:
        try:
            value = float(row[key])
        except (TypeError, ValueError, KeyError):
            return float("nan")
        return value

    out = []
    for row in table:
        tmag, sra, sdec = number(row, "Tmag"), number(row, "ra"), number(row, "dec")
        if not all(np.isfinite([tmag, sra, sdec])):
            continue
        pmra, pmdec = number(row, "pmRA"), number(row, "pmDEC")
        out.append(
            Neighbour(
                int(row["ID"]),
                sra,
                sdec,
                tmag,
                pmra if np.isfinite(pmra) else 0.0,
                pmdec if np.isfinite(pmdec) else 0.0,
            )
        )
    return out


class PixelSource:
    """Target pixels of one star, fetched sector by sector when first needed.

    ``loader(sector)`` returns a :class:`PixelData`, ``prf_loader(pixels)`` the
    PRF model for it and ``neighbour_loader(ra, dec)`` the TIC stars around the
    target. By default they download from MAST; tests pass their own. Results,
    including failures, are remembered, so several candidates of one star share
    the downloads.
    """

    def __init__(
        self,
        tic_id: int | None,
        cache_dir: str | Path | None = None,
        loader: Callable[[int], PixelData] | None = None,
        prf_loader: Callable[[PixelData], PRFModel] | None = None,
        neighbour_loader: Callable[[float, float], list[Neighbour]] | None = None,
        data: Iterable[PixelData] = (),
    ):
        self.tic_id = tic_id
        self.cache_dir = Path(cache_dir) if cache_dir is not None else default_cache_dir()
        self._loader = loader
        self._prf_loader = prf_loader
        self._neighbour_loader = neighbour_loader
        self._pixels: dict[int, PixelData | None] = {p.sector: p for p in data}
        self._errors: dict[int, str] = {}
        self._prfs: dict[int, PRFModel | None] = {}
        self._neighbours: list[Neighbour] | None = None
        self._neighbours_tried = False

    @classmethod
    def unavailable(cls, reason: str) -> PixelSource:
        """A source without pixels: the centroid test reports ``reason`` and "n/a"."""

        def loader(sector: int) -> PixelData:
            raise LookupError(reason)

        return cls(None, loader=loader)

    def get(self, sector: int) -> PixelData | None:
        """Pixels of one sector, or ``None`` (the reason is in :meth:`error`)."""
        sector = int(sector)
        if sector not in self._pixels:
            try:
                if self._loader is not None:
                    self._pixels[sector] = self._loader(sector)
                elif self.tic_id is None:
                    raise LookupError("no TIC ID")
                else:
                    self._pixels[sector] = download_tpf(
                        self.tic_id, sector, self.cache_dir / "mast"
                    )
            except Exception as exc:  # network errors, missing files, bad FITS
                log.warning("pixels of sector %d unavailable: %s", sector, exc)
                self._pixels[sector] = None
                self._errors[sector] = str(exc)
        return self._pixels[sector]

    def error(self, sector: int) -> str | None:
        return self._errors.get(int(sector))

    def prf(self, pixels: PixelData) -> PRFModel | None:
        if pixels.sector not in self._prfs:
            x, y = pixels.target_pixel()
            try:
                if self._prf_loader is not None:
                    self._prfs[pixels.sector] = self._prf_loader(pixels)
                else:
                    self._prfs[pixels.sector] = PRFModel.from_mast(
                        pixels.sector,
                        pixels.camera,
                        pixels.ccd,
                        pixels.column + x,
                        pixels.row + y,
                        self.cache_dir,
                    )
            except Exception as exc:
                log.warning("PRF model for sector %d unavailable: %s", pixels.sector, exc)
                self._prfs[pixels.sector] = None
                self._errors[pixels.sector] = f"PRF model unavailable ({exc})"
        return self._prfs[pixels.sector]

    def neighbours(self, ra: float, dec: float) -> list[Neighbour] | None:
        """TIC stars around the target, or ``None`` if they could not be looked up."""
        if not self._neighbours_tried:
            self._neighbours_tried = True
            try:
                loader = self._neighbour_loader or query_neighbours
                self._neighbours = loader(ra, dec)
            except Exception as exc:
                log.warning("TIC query for stars around the target failed: %s", exc)
                self._neighbours = None
        return self._neighbours
