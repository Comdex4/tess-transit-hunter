"""Stellar and planetary reference data: TIC, NASA Exoplanet Archive, TOI catalog.

Network access (``mast.stsci.edu`` for the TIC, ``exoplanetarchive.ipac.caltech.edu``
for confirmed planets and TOIs) is only needed by the ``query_*`` functions,
which import astroquery lazily. Everything that interprets the returned tables
is a pure function so it can be tested offline.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .utils import RHO_SUN

log = logging.getLogger(__name__)

#: log10 of the solar surface gravity in cgs units (IAU 2015 nominal: GM_sun / R_sun^2).
LOGG_SUN = 4.438


@dataclass
class StellarParams:
    """Host-star parameters in solar units (and K, dex).

    Uncertainties are 1-sigma; ``None`` means unknown. ``source`` records where
    the numbers came from so that reports can cite them.
    """

    radius: float | None = None
    radius_err: float | None = None
    mass: float | None = None
    mass_err: float | None = None
    teff: float | None = None
    teff_err: float | None = None
    logg: float | None = None
    logg_err: float | None = None
    density: float | None = None
    density_err: float | None = None
    tmag: float | None = None
    source: str = "unknown"

    def density_solar(self) -> tuple[float | None, float | None]:
        """Mean density (solar units) and its uncertainty.

        Preference order: a catalogue density; mass and radius
        (``rho = M / R^3``); surface gravity and radius (``rho = g / R``, both in
        solar units). Uncertainties are propagated to first order.
        """
        if _ok(self.density):
            return self.density, self.density_err if _ok(self.density_err) else None
        if _ok(self.mass) and _ok(self.radius):
            rho = self.mass / self.radius**3
            if _ok(self.mass_err) and _ok(self.radius_err):
                rel = math.hypot(self.mass_err / self.mass, 3 * self.radius_err / self.radius)
                return rho, rho * rel
            return rho, None
        if _ok(self.logg) and _ok(self.radius):
            rho = 10 ** (self.logg - LOGG_SUN) / self.radius
            if _ok(self.logg_err) and _ok(self.radius_err):
                rel = math.hypot(math.log(10) * self.logg_err, self.radius_err / self.radius)
                return rho, rho * rel
            return rho, None
        return None, None

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        rho, rho_err = self.density_solar()
        out["density_derived"] = rho
        out["density_derived_err"] = rho_err
        return out


def _ok(value: Any) -> bool:
    return value is not None and isinstance(value, int | float) and math.isfinite(value)


def to_float(value: Any) -> float | None:
    """Convert table cells (masked, Quantity, str, numpy scalars) to float or None."""
    if value is None:
        return None
    if np.ma.is_masked(value):
        return None
    if hasattr(value, "mask") and np.all(getattr(value, "mask", False)):
        return None
    if hasattr(value, "unmasked"):
        value = value.unmasked
    if hasattr(value, "value"):
        value = value.value
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def symmetric_error(err1: Any, err2: Any) -> float | None:
    """Average of the absolute upper/lower uncertainties reported by an archive."""
    values = [abs(v) for v in (to_float(err1), to_float(err2)) if v is not None]
    return float(np.mean(values)) if values else None


def stellar_params_from_header(header: dict[str, Any]) -> StellarParams:
    """Fallback stellar parameters from the SPOC FITS header (no uncertainties)."""
    return StellarParams(
        radius=to_float(header.get("radius")),
        teff=to_float(header.get("teff")),
        logg=to_float(header.get("logg")),
        tmag=to_float(header.get("tmag")),
        source="SPOC light-curve header (TIC values, no uncertainties)",
    )


# --------------------------------------------------------------------------- TIC
def stellar_params_from_tic_row(row: Any) -> StellarParams:
    """Interpret one row of the TIC v8 catalogue (as returned by astroquery.mast).

    TIC radii and masses are in solar units and ``rho`` is the mean density in
    solar units (Stassun et al. 2019, AJ 158, 138).
    """

    def get(name: str) -> float | None:
        try:
            return to_float(row[name])
        except (KeyError, IndexError, ValueError):
            return None

    return StellarParams(
        radius=get("rad"),
        radius_err=get("e_rad"),
        mass=get("mass"),
        mass_err=get("e_mass"),
        teff=get("Teff"),
        teff_err=get("e_Teff"),
        logg=get("logg"),
        logg_err=get("e_logg"),
        density=get("rho"),
        density_err=get("e_rho"),
        tmag=get("Tmag"),
        source="TIC v8 (MAST catalogs)",
    )


def query_tic(tic_id: int) -> StellarParams:
    """Stellar parameters of a TIC target from MAST (requires network access)."""
    from astroquery.mast import Catalogs

    table = Catalogs.query_criteria(catalog="TIC", ID=int(tic_id))
    if len(table) == 0:
        raise LookupError(f"TIC {tic_id} not found in the TIC catalogue")
    return stellar_params_from_tic_row(table[0])


def get_stellar_params(tic_id: int, header: dict[str, Any] | None = None) -> StellarParams:
    """TIC parameters, falling back to the SPOC FITS-header values if the query fails."""
    try:
        return query_tic(tic_id)
    except Exception as exc:  # network errors, service outages, missing target
        log.warning("TIC query for %s failed (%s); using header values", tic_id, exc)
    if header:
        return stellar_params_from_header(header)
    return StellarParams(source="unavailable")


# --------------------------------------------------------------------------- confirmed planets
#: Columns of the NASA Exoplanet Archive ``pscomppars`` table that are used.
PLANET_COLUMNS = (
    "pl_name",
    "hostname",
    "tic_id",
    "tran_flag",
    "pl_orbper",
    "pl_orbpererr1",
    "pl_orbpererr2",
    "pl_tranmid",
    "pl_tranmiderr1",
    "pl_tranmiderr2",
    "pl_trandep",
    "pl_trandeperr1",
    "pl_trandeperr2",
    "pl_trandur",
    "pl_ratror",
    "pl_ratrorerr1",
    "pl_ratrorerr2",
    "pl_rade",
    "pl_radeerr1",
    "pl_radeerr2",
    "pl_ratdor",
    "pl_imppar",
    "st_rad",
    "st_raderr1",
    "st_raderr2",
    "st_mass",
    "st_masserr1",
    "st_masserr2",
    "st_dens",
    "st_denserr1",
    "st_denserr2",
    "st_teff",
    "st_tefferr1",
    "st_tefferr2",
    "st_logg",
    "st_loggerr1",
    "st_loggerr2",
    "sy_tmag",
)

#: BTJD = BJD_TDB - 2457000.
BTJD_OFFSET = 2457000.0
#: Mean solar density in g cm^-3 (the archive quotes st_dens in g cm^-3).
RHO_SUN_CGS = RHO_SUN / 1000.0


@dataclass
class PublishedPlanet:
    """Reference parameters of a confirmed planet (NASA Exoplanet Archive)."""

    name: str
    host: str
    tic_id: int | None
    period: float | None
    period_err: float | None
    t0_btjd: float | None
    depth_ppm: float | None
    duration_hours: float | None
    rp_rs: float | None
    rp_rs_err: float | None
    rp_earth: float | None
    rp_earth_err: float | None
    a_rs: float | None
    impact: float | None
    stellar: StellarParams

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["stellar"] = self.stellar.as_dict()
        return out


def parse_tic_id(value: Any) -> int | None:
    """``'TIC 123'`` / ``123`` / ``'123'`` -> 123."""
    if value is None or np.ma.is_masked(value):
        return None
    text = str(value).strip().upper().replace("TIC", "").strip()
    try:
        return int(float(text))
    except ValueError:
        return None


def planet_from_archive_row(row: Any) -> PublishedPlanet:
    """Interpret one ``pscomppars`` row. Transit depth there is in percent."""

    def get(name: str) -> Any:
        try:
            return row[name]
        except (KeyError, IndexError, ValueError):
            return None

    t0 = to_float(get("pl_tranmid"))
    depth_pct = to_float(get("pl_trandep"))
    dens = to_float(get("st_dens"))
    dens_err = symmetric_error(get("st_denserr1"), get("st_denserr2"))
    stellar = StellarParams(
        radius=to_float(get("st_rad")),
        radius_err=symmetric_error(get("st_raderr1"), get("st_raderr2")),
        mass=to_float(get("st_mass")),
        mass_err=symmetric_error(get("st_masserr1"), get("st_masserr2")),
        teff=to_float(get("st_teff")),
        teff_err=symmetric_error(get("st_tefferr1"), get("st_tefferr2")),
        logg=to_float(get("st_logg")),
        logg_err=symmetric_error(get("st_loggerr1"), get("st_loggerr2")),
        density=None if dens is None else dens / RHO_SUN_CGS,
        density_err=None if dens_err is None else dens_err / RHO_SUN_CGS,
        tmag=to_float(get("sy_tmag")),
        source="NASA Exoplanet Archive pscomppars",
    )
    return PublishedPlanet(
        name=str(get("pl_name")),
        host=str(get("hostname")),
        tic_id=parse_tic_id(get("tic_id")),
        period=to_float(get("pl_orbper")),
        period_err=symmetric_error(get("pl_orbpererr1"), get("pl_orbpererr2")),
        t0_btjd=None if t0 is None else t0 - BTJD_OFFSET,
        depth_ppm=None if depth_pct is None else depth_pct * 1e4,
        duration_hours=to_float(get("pl_trandur")),
        rp_rs=to_float(get("pl_ratror")),
        rp_rs_err=symmetric_error(get("pl_ratrorerr1"), get("pl_ratrorerr2")),
        rp_earth=to_float(get("pl_rade")),
        rp_earth_err=symmetric_error(get("pl_radeerr1"), get("pl_radeerr2")),
        a_rs=to_float(get("pl_ratdor")),
        impact=to_float(get("pl_imppar")),
        stellar=stellar,
    )


def _sql_list(values: list[str]) -> str:
    return ", ".join("'" + v.replace("'", "''") + "'" for v in values)


def query_confirmed_planets(tic_ids: Sequence[int]) -> list[PublishedPlanet]:
    """Transiting confirmed planets of the given TIC targets (requires network access).

    Uses the ``pscomppars`` table (one row per planet; parameters may be drawn
    from different references, see the archive documentation). Stars are matched
    by TIC ID because the archive's host names do not always follow the common
    name (pi Men is listed as HD 39091, HD 21749 as GJ 143).
    """
    from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive

    # All columns are requested (the table is small for a few hosts): a single
    # misspelled or renamed column in an explicit SELECT would fail the whole query,
    # whereas missing columns only leave the corresponding fields empty.
    names = [f"TIC {int(tic)}" for tic in tic_ids]
    table = NasaExoplanetArchive.query_criteria(
        table="pscomppars",
        select="*",
        where=f"tic_id in ({_sql_list(names)}) and tran_flag = 1",
    )
    return [planet_from_archive_row(row) for row in table]


# --------------------------------------------------------------------------- TOI catalog
#: Columns of the archive's TOI table that are used (``tid`` is the TIC ID).
TOI_COLUMNS = (
    "toi",
    "tid",
    "tfopwg_disp",
    "pl_orbper",
    "pl_orbpererr1",
    "pl_tranmid",
    "pl_tranmiderr1",
    "pl_trandurh",
    "pl_trandep",
    "pl_rade",
    "st_tmag",
    "st_teff",
    "st_logg",
    "st_rad",
    "ra",
    "dec",
)


@dataclass
class TOI:
    """One row of the TESS Objects of Interest catalogue (depth in ppm, times BTJD)."""

    toi: float
    tic_id: int
    disposition: str
    period: float | None
    t0_btjd: float | None
    duration_hours: float | None
    depth_ppm: float | None
    rp_earth: float | None
    tmag: float | None
    teff: float | None
    logg: float | None
    radius: float | None

    @property
    def name(self) -> str:
        return f"TOI-{self.toi:.2f}"


def toi_from_row(row: Any) -> TOI:
    def get(name: str) -> Any:
        try:
            return row[name]
        except (KeyError, IndexError, ValueError):
            return None

    t0 = to_float(get("pl_tranmid"))
    tic = next((parse_tic_id(get(k)) for k in ("tid", "tic_id") if parse_tic_id(get(k))), None)
    return TOI(
        toi=float(to_float(get("toi")) or float("nan")),
        tic_id=tic or 0,
        disposition=str(get("tfopwg_disp")).strip(),
        period=to_float(get("pl_orbper")),
        t0_btjd=None if t0 is None else t0 - BTJD_OFFSET,
        duration_hours=to_float(get("pl_trandurh")),
        depth_ppm=to_float(get("pl_trandep")),
        rp_earth=to_float(get("pl_rade")),
        tmag=to_float(get("st_tmag")),
        teff=to_float(get("st_teff")),
        logg=to_float(get("st_logg")),
        radius=to_float(get("st_rad")),
    )


def query_toi_catalog(disposition: str = "PC") -> list[TOI]:
    """TOIs with a given TFOPWG disposition from the NASA Exoplanet Archive."""
    from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive

    table = NasaExoplanetArchive.query_criteria(
        table="toi", select="*", where=f"tfopwg_disp = '{disposition}'"
    )
    return [toi_from_row(row) for row in table]


def query_tois_for_tics(tic_ids: Sequence[int]) -> list[TOI]:
    """Every TOI of the given TIC targets, whatever its disposition (requires network access)."""
    from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive

    ids = ", ".join(str(int(tic)) for tic in tic_ids)
    table = NasaExoplanetArchive.query_criteria(table="toi", select="*", where=f"tid in ({ids})")
    return [toi_from_row(row) for row in table]


def query_known_planets_for_tic(tic_id: int) -> list[PublishedPlanet]:
    """Confirmed transiting planets of one TIC target (requires network access)."""
    return query_confirmed_planets([tic_id])


def known_ephemerides(planets: list[PublishedPlanet]) -> list[tuple[float, float, float]]:
    """(period, t0 in BTJD, duration in days) of planets with a complete ephemeris."""
    out = []
    for p in planets:
        if p.period and p.t0_btjd is not None and p.duration_hours:
            out.append((p.period, p.t0_btjd, p.duration_hours / 24.0))
    return out
