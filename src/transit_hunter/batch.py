"""Search many stars and rank what survives: targets, a resumable runner, safeguards.

The pipeline was checked on a few dozen stars. A search of hundreds meets a
different problem: near the detection thresholds, false alarms outnumber new
planets. On 100 real stars without known planets, 2 gave a detection just above
the thresholds and the vetting kept both; and a new planet is likely to sit in
that same regime, because strong signals are mostly TOIs already. So a batch:

1. **Selects targets** with SPOC 2-minute light curves in chosen sectors,
   filtered on the TIC (magnitude, temperature, luminosity class), leaving out
   stars that already host a confirmed planet or a TOI unless asked.
2. **Runs the full pipeline** on each star, one report folder per star, and
   records each star's outcome, so that a stopped run resumes where it stopped.
3. **Screens every candidate** the vetting keeps (:func:`screen_candidate`):

   * cross-match with confirmed planets, TOIs of any disposition and Community
     TOIs, by TIC ID and period; a detection at 2, 3, 1/2 or 1/3 of a known
     period counts only if its transits line up with the known ones;
   * a margin above the detection thresholds, in S/N and SDE;
   * at least three transits;
   * no vetting warnings, and a companion whose size could be checked;
   * the same depth in every sector (:func:`transit_hunter.vet.chunk_consistency`).

   A candidate that clears all of them is a **prospect**; the others are
   ranked for **review**, with the reasons.
4. **Summarizes** the batch at any time (``candidates.md``, ``candidates.csv``,
   ``summary.json``): prospects first, then by S/N.

None of this replaces looking at a prospect's figures, re-running it on all of
its data with full settings, and a false-positive probability.

Network access (MAST, the NASA Exoplanet Archive and ExoFOP) is only needed by
the ``query_*`` functions; everything else is testable offline.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import math
import time
import traceback
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from .catalog import (
    BTJD_OFFSET,
    StellarParams,
    get_stellar_params,
    parse_tic_id,
    planet_from_archive_row,
    to_float,
    toi_from_row,
)
from .data import NoDataError, fetch_lightcurve
from .lightcurve import LightCurve
from .pipeline import PipelineConfig, prune_report_figures, run_on_lightcurve
from .pixels import PixelSource
from .utils import write_json

log = logging.getLogger(__name__)

CTOI_URL = "https://exofop.ipac.caltech.edu/tess/download_ctoi.php?sort=ctoi&output=csv"
STATUS_FILE = "status.json"
TIERS = ("prospect", "review", "known", "rejected")
#: Ratios of a detection's period to a known one that count as the same object.
HARMONICS = (1.0, 2.0, 0.5, 3.0, 1.0 / 3.0)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- sectors
def parse_sectors(text: str) -> list[int]:
    """``"1-13,20,40-42"`` -> ``[1, 2, ..., 13, 20, 40, 41, 42]``."""
    out: set[int] = set()
    for part in text.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            lo, hi = (int(x) for x in part.split("-", 1))
            if hi < lo:
                raise ValueError(f"bad sector range {part!r}")
            out.update(range(lo, hi + 1))
        else:
            out.add(int(part))
    return sorted(out)


def query_sector_targets(sector: int) -> set[int]:
    """TIC IDs with a SPOC 2-minute light curve in ``sector`` (requires network access)."""
    from astroquery.mast import Observations

    obs = Observations.query_criteria(
        obs_collection="TESS",
        dataproduct_type="timeseries",
        sequence_number=sector,
        provenance_name="SPOC",
    )
    out = set()
    for name, exptime in zip(obs["target_name"], obs["t_exptime"], strict=True):
        tic = parse_tic_id(name)
        if tic and exptime == 120:
            out.add(tic)
    return out


def sector_targets(
    sector: int, cache_dir: Path | None = None, query: Callable[[int], set[int]] | None = None
) -> set[int]:
    """TIC IDs with 2-minute data in ``sector``, cached as JSON in ``cache_dir``."""
    path = None if cache_dir is None else Path(cache_dir) / f"sector_{sector:03d}.json"
    if path is not None and path.exists():
        return set(json.loads(path.read_text()))
    tics = (query or query_sector_targets)(sector)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(sorted(tics)))
    return tics


# --------------------------------------------------------------------------- targets
@dataclass
class Target:
    """One star of a batch: TIC ID, catalog values and its 2-minute sectors."""

    tic_id: int
    tmag: float = math.nan
    teff: float = math.nan
    radius: float = math.nan
    sectors: list[int] = field(default_factory=list)


TARGET_FIELDS = ("tic_id", "tmag", "teff", "radius", "sectors")


def write_targets(path: str | Path, targets: Iterable[Target]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(TARGET_FIELDS)
        for t in targets:
            writer.writerow(
                [t.tic_id, t.tmag, t.teff, t.radius, " ".join(str(s) for s in t.sectors)]
            )


def read_targets(path: str | Path) -> list[Target]:
    """Targets from a CSV written by :func:`write_targets`, or one TIC ID per line."""
    text = Path(path).read_text()
    first = text.lstrip().splitlines()[0] if text.strip() else ""
    if not first.startswith("tic_id"):
        ids = [parse_tic_id(line.split("#")[0]) for line in text.splitlines()]
        return [Target(t) for t in ids if t]
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        out.append(
            Target(
                tic_id=int(row["tic_id"]),
                tmag=float(row.get("tmag") or math.nan),
                teff=float(row.get("teff") or math.nan),
                radius=float(row.get("radius") or math.nan),
                sectors=[int(s) for s in (row.get("sectors") or "").split()],
            )
        )
    return out


@dataclass
class Selection:
    """Which stars to search. Magnitudes and temperatures are inclusive limits."""

    sectors: list[int]
    min_sectors: int = 1
    tmag_max: float = 13.0
    tmag_min: float | None = None
    teff_min: float | None = None
    teff_max: float | None = None
    lumclass: str | None = "DWARF"
    n: int | None = None
    seed: int = 1
    exclude_known_hosts: bool = True

    def describe(self) -> str:
        span = f"{self.sectors[0]}–{self.sectors[-1]}" if self.sectors else "none"
        parts = [f"SPOC 2-minute light curves in at least {self.min_sectors} of sectors {span}"]
        mag = f"Tmag <= {self.tmag_max:g}"
        if self.tmag_min is not None:
            mag = f"{self.tmag_min:g} <= {mag}"
        parts.append(mag)
        if self.teff_min is not None or self.teff_max is not None:
            lo = "" if self.teff_min is None else f"{self.teff_min:g} K <= "
            hi = "" if self.teff_max is None else f" <= {self.teff_max:g} K"
            parts.append(f"{lo}Teff{hi}")
        if self.lumclass:
            parts.append(f"TIC luminosity class {self.lumclass}")
        if self.exclude_known_hosts:
            parts.append("no confirmed planet and no TOI of any disposition")
        count = "all" if self.n is None else f"{self.n}"
        parts.append(f"{count} drawn at random (seed {self.seed}) from the stars sorted by TIC ID")
        return "; ".join(parts)

    def accepts(self, row: dict[str, Any]) -> bool:
        tmag, teff = row.get("tmag", math.nan), row.get("teff", math.nan)
        if not (math.isfinite(tmag) and tmag <= self.tmag_max):
            return False
        if self.tmag_min is not None and tmag < self.tmag_min:
            return False
        if self.teff_min is not None and not (math.isfinite(teff) and teff >= self.teff_min):
            return False
        if self.teff_max is not None and not (math.isfinite(teff) and teff <= self.teff_max):
            return False
        return not (self.lumclass and row.get("lumclass") != self.lumclass)


def query_tic_rows(tic_ids: Sequence[int]) -> dict[int, dict[str, Any]]:
    """Tmag, Teff, radius and luminosity class from the TIC (requires network access)."""
    from astroquery.mast import Catalogs

    table = Catalogs.query_criteria(catalog="Tic", ID=[int(t) for t in tic_ids])
    out = {}
    for row in table:
        out[int(row["ID"])] = {
            "tmag": to_float(row["Tmag"]) or math.nan,
            "teff": to_float(row["Teff"]) or math.nan,
            "radius": to_float(row["rad"]) or math.nan,
            "lumclass": str(row["lumclass"]),
        }
    return out


def select_targets(
    selection: Selection,
    known_hosts: set[int],
    sector_lists: Callable[[int], set[int]],
    tic_rows: Callable[[Sequence[int]], dict[int, dict[str, Any]]] = query_tic_rows,
    report: Callable[[str], None] = print,
    chunk: int = 200,
) -> list[Target]:
    """Stars meeting ``selection``, in a random but reproducible order."""
    sectors_of: dict[int, list[int]] = defaultdict(list)
    for sector in selection.sectors:
        tics = sector_lists(sector)
        report(f"sector {sector}: {len(tics)} stars with 2-minute data")
        for tic in tics:
            sectors_of[tic].append(sector)
    pool = sorted(
        tic
        for tic, found in sectors_of.items()
        if len(found) >= selection.min_sectors
        and not (selection.exclude_known_hosts and tic in known_hosts)
    )
    report(f"{len(pool)} stars in at least {selection.min_sectors} of these sectors")
    order = np.random.default_rng(selection.seed).permutation(len(pool))
    chosen: list[Target] = []
    for start in range(0, len(order), chunk):
        batch = [pool[i] for i in order[start : start + chunk]]
        rows = tic_rows(batch)
        for tic in batch:  # keep the random order
            row = rows.get(tic)
            if row is None or not selection.accepts(row):
                continue
            chosen.append(
                Target(tic, row["tmag"], row["teff"], row["radius"], sorted(sectors_of[tic]))
            )
            if selection.n is not None and len(chosen) >= selection.n:
                return chosen
        report(f"  checked {min(start + chunk, len(order))} stars in the TIC: {len(chosen)} kept")
    return chosen


# --------------------------------------------------------------------------- known objects
@dataclass
class KnownObject:
    """A confirmed planet, TOI or Community TOI (CTOI); times in BTJD."""

    kind: str
    name: str
    tic_id: int
    period: float | None = None
    t0_btjd: float | None = None
    disposition: str = ""

    def label(self) -> str:
        text = self.name if not self.disposition else f"{self.name} ({self.disposition})"
        if self.period:
            text += f", P = {self.period:.4f} d"
        return text


def _btjd(value: Any) -> float | None:
    t = to_float(value)
    if t is None:
        return None
    return t - BTJD_OFFSET if t > 2_000_000 else t


def ctois_from_csv(text: str) -> list[KnownObject]:
    """Parse ExoFOP's CTOI table (CSV). CTOIs promoted to TOIs are named as such."""
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        tic = parse_tic_id(row.get("TIC ID"))
        if not tic:
            continue
        promoted = (row.get("Promoted to TOI") or "").strip()
        name = f"CTOI {(row.get('CTOI') or '').strip()}"
        if promoted and promoted not in ("0", "0.0"):
            name += f" (TOI-{promoted})"
        disposition = (row.get("TFOPWG Disposition") or row.get("User Disposition") or "").strip()
        out.append(
            KnownObject(
                kind="CTOI",
                name=name,
                tic_id=tic,
                period=to_float(row.get("Period (days)")),
                t0_btjd=_btjd(row.get("Transit Epoch (BJD)")),
                disposition=disposition,
            )
        )
    return out


def query_ctois(url: str = CTOI_URL, timeout: float = 120.0) -> list[KnownObject]:
    """Every Community TOI on ExoFOP (requires network access)."""
    import requests

    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return ctois_from_csv(response.text)


def query_all_tois() -> list[KnownObject]:
    """Every TOI, whatever its disposition, from the NASA Exoplanet Archive."""
    from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive

    table = NasaExoplanetArchive.query_criteria(
        table="toi", select="toi,tid,tfopwg_disp,pl_orbper,pl_tranmid,pl_trandurh"
    )
    out = []
    for row in table:
        toi = toi_from_row(row)
        if toi.tic_id:
            out.append(
                KnownObject("TOI", toi.name, toi.tic_id, toi.period, toi.t0_btjd, toi.disposition)
            )
    return out


def query_all_planets() -> list[KnownObject]:
    """Every confirmed planet with a TIC ID in the NASA Exoplanet Archive (pscomppars)."""
    from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive

    table = NasaExoplanetArchive.query_criteria(
        table="pscomppars", select="pl_name,hostname,tic_id,pl_orbper,pl_tranmid"
    )
    out = []
    for row in table:
        planet = planet_from_archive_row(row)
        if planet.tic_id:
            out.append(
                KnownObject("planet", planet.name, planet.tic_id, planet.period, planet.t0_btjd)
            )
    return out


@dataclass
class KnownCatalog:
    """Known planets, TOIs and CTOIs, indexed by TIC ID.

    ``sources`` says where each kind came from and when, or why it is missing: a
    batch whose catalog is incomplete cannot call anything new.
    """

    objects: list[KnownObject] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._by_tic: dict[int, list[KnownObject]] = defaultdict(list)
        for obj in self.objects:
            self._by_tic[obj.tic_id].append(obj)

    KINDS = ("planet", "TOI", "CTOI")

    def available(self, kind: str) -> bool:
        return not self.sources.get(kind, "unavailable").startswith("unavailable")

    @property
    def complete(self) -> bool:
        return all(self.available(k) for k in self.KINDS)

    def missing(self) -> list[str]:
        return [k for k in self.KINDS if not self.available(k)]

    def for_tic(self, tic_id: int) -> list[KnownObject]:
        return list(self._by_tic.get(int(tic_id), []))

    def hosts(self, kinds: Sequence[str] = ("planet", "TOI")) -> set[int]:
        return {o.tic_id for o in self.objects if o.kind in kinds}

    def save(self, path: str | Path) -> None:
        write_json(
            path,
            {"sources": self.sources, "objects": [asdict(o) for o in self.objects]},
        )

    @classmethod
    def load(cls, path: str | Path) -> KnownCatalog:
        data = json.loads(Path(path).read_text())
        return cls([KnownObject(**o) for o in data["objects"]], data["sources"])


def fetch_known_catalog(
    queries: dict[str, Callable[[], list[KnownObject]]] | None = None,
    report: Callable[[str], None] = print,
) -> KnownCatalog:
    """Download the three catalogs; a failed download is recorded, not raised."""
    queries = queries or {
        "planet": query_all_planets,
        "TOI": query_all_tois,
        "CTOI": query_ctois,
    }
    names = {
        "planet": "confirmed planets (NASA Exoplanet Archive)",
        "TOI": "TOIs (NASA Exoplanet Archive)",
        "CTOI": "Community TOIs (ExoFOP)",
    }
    objects: list[KnownObject] = []
    sources = {}
    for kind, query in queries.items():
        try:
            found = query()
        except Exception as exc:  # network errors, service outages
            sources[kind] = f"unavailable ({type(exc).__name__}: {exc})"
            report(f"{names.get(kind, kind)}: {sources[kind]}")
            continue
        objects += found
        sources[kind] = f"{len(found)} {names.get(kind, kind)}, downloaded {_now()}"
        report(sources[kind])
    return KnownCatalog(objects, sources)


def load_or_fetch_catalog(
    path: str | Path,
    max_age_days: float = 7.0,
    refresh: bool = False,
    fetch: Callable[[], KnownCatalog] = fetch_known_catalog,
) -> KnownCatalog:
    """The catalog saved at ``path``, downloaded again if missing, stale or incomplete."""
    path = Path(path)
    if path.exists() and not refresh:
        age_days = (time.time() - path.stat().st_mtime) / 86400
        catalog = KnownCatalog.load(path)
        if age_days <= max_age_days and catalog.complete:
            return catalog
    catalog = fetch()
    catalog.save(path)
    return catalog


def match_known(
    period: float,
    t0: float | None,
    duration: float,
    objects: Iterable[KnownObject],
    tolerance: float = 0.01,
    harmonic_tolerance: float = 0.002,
) -> tuple[KnownObject, float] | None:
    """The known object a detection corresponds to, and the ratio of their periods.

    The same period (within ``tolerance``, relative) matches whatever the phase,
    since a detection half an orbit off is the known object's other eclipse. A
    period 2, 3, 1/2 or 1/3 times a known one (within ``harmonic_tolerance``)
    matches only if the transits line up, that is if the two epochs differ by a
    whole number of the shorter period: two planets near a 2:1 resonance, like
    TOI-270 c and d, have periods about twice each other's but transits that do
    not coincide.
    """
    best: tuple[KnownObject, float] | None = None
    for obj in objects:
        if not obj.period or obj.period <= 0:
            continue
        ratio = period / obj.period
        for h in HARMONICS:
            if h == 1.0:
                if abs(ratio - 1.0) < tolerance:
                    return obj, 1.0
                continue
            if abs(ratio / h - 1.0) >= harmonic_tolerance or t0 is None or obj.t0_btjd is None:
                continue
            shorter = obj.period * min(h, 1.0)
            offset = (t0 - obj.t0_btjd) / shorter
            miss = abs(offset - round(offset)) * shorter
            if miss < max(duration, 0.05) and best is None:
                best = (obj, h)
    return best


# --------------------------------------------------------------------------- screening
@dataclass
class ScreenConfig:
    """What a candidate must clear to be a prospect.

    The margins sit above the strongest noise peaks seen on 100 real stars
    without known planets (S/N up to 8.8, SDE up to 7.9); the two false alarms
    there had S/N 7.7 and 8.5 and SDE 7.8 and 7.9.
    """

    min_snr: float = 10.0
    min_sde: float = 9.0
    min_transits: int = 3
    min_snr_without_strongest_chunk: float = 3.0
    max_chunk_p: float = 1e-3
    period_tolerance: float = 0.01
    harmonic_tolerance: float = 0.002


def screen_candidate(
    entry: dict[str, Any],
    known: Sequence[KnownObject] = (),
    config: ScreenConfig | None = None,
    missing_catalogs: Sequence[str] = (),
) -> dict[str, Any]:
    """Tier of one candidate (see :data:`TIERS`) and the reasons behind it."""
    config = config or ScreenConfig()
    sig = entry["signal"]
    vetting = entry.get("vetting") or {}
    tests = {t["name"]: t for t in vetting.get("tests", [])}
    verdict = vetting.get("verdict", "")
    match = match_known(
        sig["period"],
        sig.get("t0"),
        sig.get("duration", 0.1),
        known,
        config.period_tolerance,
        config.harmonic_tolerance,
    )
    others = [o.label() for o in known if match is None or o is not match[0]]
    reasons: list[str] = []
    notes = [
        f"not tested: {name} ({t.get('message', '')})"
        for name, t in tests.items()
        if t.get("status") == "n/a" and name != "rotation"
    ]
    if others:
        notes.append("the star also has " + "; ".join(others))
    if match is not None:
        obj, ratio = match
        tier = "known"
        reasons.append(obj.label() if ratio == 1.0 else f"{ratio:g} × the period of {obj.label()}")
    elif verdict == "likely false positive":
        tier = "rejected"
        failed = [n for n, t in tests.items() if t.get("status") == "fail"]
        reasons.append("failed: " + (", ".join(failed) or "vetting"))
    else:
        if sig["snr"] < config.min_snr:
            reasons.append(f"S/N {sig['snr']:.1f} is below the margin of {config.min_snr:g}")
        if sig["sde"] < config.min_sde:
            reasons.append(f"SDE {sig['sde']:.1f} is below the margin of {config.min_sde:g}")
        n_transits = int(sig.get("n_transits") or 0)
        if n_transits < config.min_transits:
            reasons.append(f"only {n_transits} transits")
        warnings = [n for n, t in tests.items() if t.get("status") == "warn"]
        if warnings:
            reasons.append("vetting warnings: " + ", ".join(warnings))
        if all(tests.get(n, {}).get("status") == "n/a" for n in ("density", "radius")):
            reasons.append("the companion's size could not be checked (no stellar radius)")
        reasons += _chunk_reasons(entry.get("chunks"), config)
        if missing_catalogs:
            reasons.append("not cross-matched with: " + ", ".join(missing_catalogs))
        tier = "review" if reasons else "prospect"
    return {
        "tier": tier,
        "reasons": reasons,
        "notes": notes,
        "match": None if match is None else match[0].name,
        "match_ratio": None if match is None else match[1],
    }


def _chunk_reasons(chunks: dict[str, Any] | None, config: ScreenConfig) -> list[str]:
    if not chunks or not chunks.get("n_transits"):
        return ["consistency across sectors not measured"]
    if chunks["n_chunks"] < 2:
        return ["all transits in one stretch of data, so their consistency cannot be checked"]
    out = []
    without = chunks["snr_without_strongest"]
    if not (math.isfinite(without) and without >= config.min_snr_without_strongest_chunk):
        out.append(f"the signal rests on {chunks['strongest']}: S/N {without:.1f} without it")
    p = chunks.get("p_value")
    if p is not None and p < config.max_chunk_p:
        out.append(f"the depth differs between {chunks['chunked_by']}s (p = {p:.1g})")
    return out


# --------------------------------------------------------------------------- running
def choose_sectors(sectors: Sequence[int], max_sectors: int | None) -> list[int] | None:
    """The sectors to search: all known ones, or the latest ``max_sectors``; None = all."""
    if not sectors:
        return None
    chosen = sorted(int(s) for s in sectors)
    if max_sectors and len(chosen) > max_sectors:
        chosen = chosen[-max_sectors:]
    return chosen


def star_folder(out: str | Path, tic_id: int) -> Path:
    return Path(out) / "stars" / f"TIC_{int(tic_id)}"


def read_status(folder: Path) -> dict[str, Any] | None:
    """A star's recorded outcome, or None if it is to be searched (again).

    Only ``status.json`` counts. It is written last, so a star stopped before
    it, even one with a complete ``report.json``, is searched again; and a file
    cut short (the computer stopped while writing it) counts as missing.
    """
    try:
        status = json.loads((folder / STATUS_FILE).read_text())
    except (OSError, ValueError):
        return None
    return status if isinstance(status, dict) and "status" in status else None


def _write_status(folder: Path, status: dict[str, Any]) -> None:
    """Write ``status.json`` so that it is either complete or absent, never cut short."""
    tmp = folder / (STATUS_FILE + ".tmp")
    write_json(tmp, status)
    tmp.replace(folder / STATUS_FILE)


_REPORT_KEYS = ("target", "search", "planets")


def _read_report(path: Path) -> dict[str, Any] | None:
    """A star's ``report.json``, or None if it is missing, cut short or not a report."""
    try:
        report = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(report, dict) or not all(k in report for k in _REPORT_KEYS):
        return None
    return report


def is_finished(out: str | Path, target: Target, retry_failed: bool = False) -> bool:
    """Whether a star's outcome is recorded (a searched star also needs a readable report)."""
    folder = star_folder(out, target.tic_id)
    status = read_status(folder)
    if status is None:
        return False
    if status.get("status") == "searched" and _read_report(folder / "report.json") is None:
        return False
    # Every selected star is listed with 2-minute data, so "no data" is retried too.
    return not (retry_failed and status.get("status") in ("error", "no data"))


def run_star(
    target: Target,
    folder: Path,
    config: PipelineConfig,
    cache_dir: str | Path | None = None,
    max_sectors: int | None = None,
    fetch: Callable[..., LightCurve] = fetch_lightcurve,
    stellar_params: Callable[[int, Any], StellarParams] = get_stellar_params,
    pixel_source: Callable[[int, Any], PixelSource] | None = None,
) -> dict[str, Any]:
    """Search one star; returns its status. Stars with no candidate keep no figures."""
    sectors = choose_sectors(target.sectors, max_sectors)
    lc = fetch(target.tic_id, cache_dir=cache_dir, sectors=sectors, config=config.cleaning)
    stellar = stellar_params(target.tic_id, lc.meta.get("stellar_header"))
    pixels = (pixel_source or _default_pixels)(target.tic_id, cache_dir)
    report = run_on_lightcurve(
        lc, folder, stellar, config, name=f"TIC {target.tic_id}", pixels=pixels
    )
    candidates = [p for p in report["planets"] if p.get("role") == "candidate"]
    if not candidates:
        prune_report_figures(folder, report, set())
    return {
        "status": "searched",
        "sectors": lc.sectors,
        "n_detections": report["search"]["n_detections"],
        "n_candidates": len(candidates),
        "candidates": [
            {
                "period": p["signal"]["period"],
                "snr": p["signal"]["snr"],
                "verdict": p["vetting"]["verdict"],
            }
            for p in candidates
        ],
    }


def _default_pixels(tic_id: int, cache_dir: Any) -> PixelSource:
    return PixelSource(tic_id, cache_dir=cache_dir)


def _duration(seconds: float) -> str:
    if seconds < 90:
        return f"{seconds:.0f} s"
    if seconds < 5400:
        return f"{seconds / 60:.0f} min"
    return f"{seconds / 3600:.1f} h"


def _status_line(status: dict[str, Any]) -> str:
    kind = status["status"]
    if kind != "searched":
        return f"{kind}: {status.get('message', '')}"
    if not status.get("candidates"):
        return "no detection" if not status.get("n_detections") else "no candidate"
    return "; ".join(
        f"P = {c['period']:.4f} d, S/N {c['snr']:.1f}: {c['verdict']}" for c in status["candidates"]
    )


def _looks_like_outage(exc: BaseException) -> bool:
    """A network or disk failure, which waiting can cure, as opposed to a bug."""
    if isinstance(exc, OSError):  # connection errors, timeouts, disk full
        return True
    name = type(exc).__name__
    return any(word in name for word in ("Timeout", "Connection", "HTTP", "Remote"))


def _search_star(
    target: Target,
    folder: Path,
    config: PipelineConfig,
    cache_dir: str | Path | None,
    max_sectors: int | None,
    star_kwargs: dict[str, Any],
) -> dict[str, Any]:
    try:
        return run_star(target, folder, config, cache_dir, max_sectors, **star_kwargs)
    except NoDataError as exc:
        return {"status": "no data", "message": str(exc)}
    except Exception as exc:  # one bad star must not stop the batch
        return {
            "status": "error",
            "message": f"{type(exc).__name__}: {exc}",
            "outage": _looks_like_outage(exc),
            "traceback": traceback.format_exc(),
        }


def run_batch(
    targets: Sequence[Target],
    out: str | Path,
    config: PipelineConfig,
    cache_dir: str | Path | None = None,
    max_sectors: int | None = None,
    max_hours: float | None = None,
    retry_failed: bool = False,
    summarize: Callable[[], Any] | None = None,
    summarize_every: int = 25,
    report: Callable[[str], None] = print,
    pause_after: int = 3,
    pause_seconds: float = 600.0,
    max_pauses: int = 6,
    sleep: Callable[[float], Any] = time.sleep,
    **star_kwargs: Any,
) -> dict[str, int]:
    """Search every target not finished yet; safe to stop and run again.

    Each star's outcome goes to ``stars/TIC_<id>/status.json`` as soon as it is
    known, so an interrupted batch resumes with the next unfinished star. A star
    that raised an error or found no data is skipped on later runs unless
    ``retry_failed``. ``max_hours`` stops the batch after the star that crosses
    the limit.

    When ``pause_after`` stars in a row fail with a network or disk error, an
    archive is probably down: the batch waits ``pause_seconds`` and tries the
    same star again, rather than marking every remaining star as failed. After
    ``max_pauses`` waits without success it stops, to be run again later.
    """
    out = Path(out)
    todo = [t for t in targets if not is_finished(out, t, retry_failed)]
    report(f"{len(targets)} targets: {len(targets) - len(todo)} done before, {len(todo)} to go")
    logfile = out / "batch.log"
    counts: dict[str, int] = defaultdict(int)
    started = time.monotonic()
    streak = 0  # stars in a row that failed with a network or disk error
    for i, target in enumerate(todo, 1):
        if max_hours is not None and time.monotonic() - started > max_hours * 3600:
            report(f"stopping: the {max_hours:g}-hour limit is reached; run again to continue")
            break
        folder = star_folder(out, target.tic_id)
        folder.mkdir(parents=True, exist_ok=True)
        t_star = time.monotonic()
        pauses = 0
        while True:
            status = _search_star(target, folder, config, cache_dir, max_sectors, star_kwargs)
            if not status.get("outage"):
                streak = 0
                break
            streak += 1
            if streak < pause_after or pauses >= max_pauses:
                break
            pauses += 1
            report(
                f"{streak} failures in a row ({status['message']}); an archive may be down: "
                f"waiting {_duration(pause_seconds)}, then trying TIC {target.tic_id} again"
            )
            sleep(pause_seconds)
        status["finished_utc"] = _now()
        status["wall_s"] = time.monotonic() - t_star
        _write_status(folder, status)
        counts[status["status"]] += 1
        elapsed = time.monotonic() - started
        left = elapsed / i * (len(todo) - i)
        line = (
            f"[{i}/{len(todo)}] TIC {target.tic_id}: {_status_line(status)} "
            f"({_duration(status['wall_s'])}; about {_duration(left)} left)"
        )
        report(line)
        with logfile.open("a") as handle:
            handle.write(f"{status['finished_utc']} {line}\n")
        if summarize is not None and i % summarize_every == 0:
            _try_summarize(summarize, report)
        if status.get("outage") and pauses >= max_pauses and max_pauses > 0:
            report(
                f"stopping: stars have kept failing for {_duration(pauses * pause_seconds)} "
                f"({status['message']}); run again later with --retry-failed"
            )
            break
    if summarize is not None:
        _try_summarize(summarize, report)
    return dict(counts)


def _try_summarize(summarize: Callable[[], Any], report: Callable[[str], None]) -> None:
    """Rewrite the tables; a failure there must not stop the search."""
    try:
        summarize()
    except Exception as exc:
        report(f"could not update the tables ({type(exc).__name__}: {exc}); the search goes on")


# --------------------------------------------------------------------------- summary
def _top_peak(report: dict[str, Any]) -> dict[str, float]:
    signals = report.get("search", {}).get("signals") or []
    top = signals[0] if signals else {}
    return {k: float(top.get(k, math.nan)) for k in ("period", "snr", "sde")}


def _rp_earth(entry: dict[str, Any]) -> float:
    posterior = (entry.get("fit") or {}).get("posterior") or {}
    value = (posterior.get("rp_earth") or {}).get("median")
    return float(value) if value is not None else math.nan


def collect_batch(out: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Every star folder's outcome, and every candidate with its report and folder."""
    out = Path(out)
    stars, candidates = [], []
    for folder in sorted((out / "stars").glob("TIC_*")):
        status = read_status(folder)
        if status is None:
            continue
        tic = int(folder.name.split("_", 1)[1])
        row: dict[str, Any] = {
            "tic_id": tic,
            "status": status.get("status"),
            "message": status.get("message", ""),
        }
        path = folder / "report.json"
        if status.get("status") == "searched":
            report = _read_report(path)
            if report is None:
                row.update(status="unreadable", message="report.json is missing or cut short")
                stars.append(row)
                continue
            peak = _top_peak(report)
            row.update(
                sectors=" ".join(str(s) for s in report["target"].get("sectors") or []),
                n_points=report["target"].get("n_points"),
                cdpp_1h_ppm=report.get("noise", {}).get("robust_cdpp_ppm", {}).get("1h"),
                top_period=peak["period"],
                top_snr=peak["snr"],
                top_sde=peak["sde"],
                n_detections=report["search"]["n_detections"],
                n_candidates=report["search"]["n_candidates"],
                runtime_s=report.get("runtime_s"),
            )
            n = 0
            for entry in report["planets"]:
                if entry.get("role") != "candidate":
                    continue
                n += 1
                candidates.append(
                    {"tic_id": tic, "n": n, "entry": entry, "report": report, "folder": folder}
                )
        stars.append(row)
    return stars, candidates


CANDIDATE_FIELDS = (
    "rank",
    "tier",
    "tic_id",
    "candidate",
    "period_d",
    "t0_btjd",
    "duration_h",
    "depth_ppm",
    "snr",
    "sde",
    "n_transits",
    "rp_earth",
    "verdict",
    "failed",
    "warnings",
    "match",
    "reasons",
    "notes",
    "snr_by_chunk",
    "snr_without_strongest_chunk",
    "chunk_p_value",
    "folder",
)


def candidate_row(
    item: dict[str, Any],
    screen: dict[str, Any],
    out: Path,
) -> dict[str, Any]:
    entry = item["entry"]
    sig = entry["signal"]
    tests = (entry.get("vetting") or {}).get("tests", [])
    chunks = entry.get("chunks") or {}
    return {
        "tier": screen["tier"],
        "tic_id": item["tic_id"],
        "candidate": item["n"],
        "period_d": sig["period"],
        "t0_btjd": sig.get("t0"),
        "duration_h": sig.get("duration", math.nan) * 24,
        "depth_ppm": sig["depth"] * 1e6,
        "snr": sig["snr"],
        "sde": sig["sde"],
        "n_transits": sig.get("n_transits"),
        "rp_earth": _rp_earth(entry),
        "verdict": (entry.get("vetting") or {}).get("verdict", ""),
        "failed": ", ".join(t["name"] for t in tests if t["status"] == "fail"),
        "warnings": ", ".join(t["name"] for t in tests if t["status"] == "warn"),
        "match": screen["match"] or "",
        "reasons": "; ".join(screen["reasons"]),
        "notes": "; ".join(screen["notes"]),
        "snr_by_chunk": "; ".join(
            f"{c['chunk']}: {c['snr']:.1f}" for c in chunks.get("chunks", [])
        ),
        "snr_without_strongest_chunk": chunks.get("snr_without_strongest", math.nan),
        "chunk_p_value": chunks.get("p_value"),
        "folder": str(item["folder"].relative_to(out)),
    }


def rank_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = sorted(rows, key=lambda r: (TIERS.index(r["tier"]), -r["snr"]))
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    return rows


def summarize_batch(
    out: str | Path,
    catalog: KnownCatalog,
    config: ScreenConfig | None = None,
    selection: str = "",
) -> dict[str, Any]:
    """Screen every candidate found so far and write the batch's tables."""
    out = Path(out)
    config = config or ScreenConfig()
    stars, items = collect_batch(out)
    missing = catalog.missing()
    rows = []
    for item in items:
        screen = screen_candidate(item["entry"], catalog.for_tic(item["tic_id"]), config, missing)
        rows.append(candidate_row(item, screen, out))
    rows = rank_rows(rows)
    searched = [s for s in stars if s["status"] == "searched"]
    snr = np.array([s.get("top_snr", math.nan) for s in searched], dtype=float)
    sde = np.array([s.get("top_sde", math.nan) for s in searched], dtype=float)

    def quantiles(x: np.ndarray) -> dict[str, float] | None:
        x = x[np.isfinite(x)]
        if not x.size:
            return None
        return {
            "median": float(np.median(x)),
            "p99": float(np.percentile(x, 99)),
            "max": float(np.max(x)),
        }

    by_status: dict[str, int] = defaultdict(int)
    for s in stars:
        by_status[s["status"]] += 1
    by_tier: dict[str, int] = {t: 0 for t in TIERS}
    for r in rows:
        by_tier[r["tier"]] += 1
    summary = {
        "updated_utc": _now(),
        "selection": selection,
        "stars": dict(by_status),
        "n_stars_with_detection": sum(1 for s in searched if s.get("n_detections")),
        "candidates": by_tier,
        "top_peak_snr": quantiles(snr),
        "top_peak_sde": quantiles(sde),
        "catalogs": catalog.sources,
        "screen": asdict(config),
    }
    write_json(out / "summary.json", summary)
    with (out / "candidates.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANDIDATE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    with (out / "stars.csv").open("w", newline="") as handle:
        fields = sorted({k for s in stars for k in s}, key=_STAR_FIELD_ORDER.index)
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(stars)
    (out / "candidates.md").write_text(candidates_markdown(summary, rows, stars, config))
    return summary


_STAR_FIELD_ORDER = [
    "tic_id",
    "status",
    "message",
    "sectors",
    "n_points",
    "cdpp_1h_ppm",
    "top_period",
    "top_snr",
    "top_sde",
    "n_detections",
    "n_candidates",
    "runtime_s",
]


def _fmt(value: Any, spec: str) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "–"
    return format(v, spec) if math.isfinite(v) else "–"


def candidates_markdown(
    summary: dict[str, Any],
    rows: list[dict[str, Any]],
    stars: list[dict[str, Any]],
    config: ScreenConfig,
) -> str:
    s = summary
    n_stars = sum(s["stars"].values())
    lines = [
        "# Batch search: candidates",
        "",
        f"Updated {s['updated_utc']}.",
        "",
    ]
    if s["selection"]:
        lines += [f"Selection: {s['selection']}.", ""]
    status = ", ".join(f"{v} {k}" for k, v in sorted(s["stars"].items()))
    lines += [
        f"* Stars processed: {n_stars} ({status})",
        f"* Stars with a detection: {s['n_stars_with_detection']}",
        "* Candidates: " + ", ".join(f"{s['candidates'][t]} {t}" for t in TIERS),
    ]
    if s["top_peak_snr"]:
        q, r = s["top_peak_snr"], s["top_peak_sde"]
        lines.append(
            f"* Strongest peak of each star's first search pass: S/N median {q['median']:.1f}, "
            f"99th percentile {q['p99']:.1f}, maximum {q['max']:.1f}; SDE median "
            f"{r['median']:.1f}, 99th percentile {r['p99']:.1f}, maximum {r['max']:.1f}"
        )
    lines.append("* Catalogs: " + "; ".join(f"{k}: {v}" for k, v in s["catalogs"].items()))
    lines += [
        "",
        f"A **prospect** clears every safeguard: S/N ≥ {config.min_snr:g} and SDE ≥ "
        f"{config.min_sde:g}, at least {config.min_transits} transits, no vetting warning, a "
        "companion whose size could be checked, the same depth in every sector, and no match "
        "among confirmed planets, TOIs and CTOIs. Everything the vetting keeps otherwise is "
        "listed for **review**, with the reasons.",
        "",
    ]
    titles = {
        "prospect": "Prospects",
        "review": "For review",
        "known": "Known objects found again",
        "rejected": "Rejected by the vetting",
    }
    for tier in TIERS:
        chosen = [r for r in rows if r["tier"] == tier]
        lines += [f"## {titles[tier]} ({len(chosen)})", ""]
        if not chosen:
            lines += ["None.", ""]
            continue
        lines += [
            "| rank | TIC | P (d) | depth (ppm) | Rp (R⊕) | S/N | SDE | transits | "
            "verdict | why | report |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for r in chosen:
            why = r["reasons"] or ("–" if not r["notes"] else r["notes"])
            if tier == "known":
                why = f"matches {r['reasons']}"
            lines.append(
                f"| {r['rank']} | {r['tic_id']} | {_fmt(r['period_d'], '.5f')} | "
                f"{_fmt(r['depth_ppm'], '.0f')} | {_fmt(r['rp_earth'], '.2f')} | "
                f"{_fmt(r['snr'], '.1f')} | {_fmt(r['sde'], '.1f')} | {r['n_transits']} | "
                f"{r['verdict']} | {why} | [{r['folder']}]({r['folder']}/summary.md) |"
            )
        lines.append("")
    failed = [x for x in stars if x["status"] == "error"]
    if failed:
        lines += [f"## Stars that failed ({len(failed)})", ""]
        lines += [f"* TIC {x['tic_id']}: {x['message']}" for x in failed]
        lines += ["", "Run again with `--retry-failed` to try them once more.", ""]
    lines += [
        "## Before trusting a prospect",
        "",
        "1. Open its report folder: the search summary, the folded transit, the fit, the "
        "vetting panels and the centroid figure. The transits should be visible, similar to "
        "each other and not at the edges of the data.",
        "2. Run it alone on all of its data with full settings: `transit-hunter run --tic <TIC>`.",
        "3. Look the star up on ExoFOP (exofop.ipac.caltech.edu/tess): TOIs and CTOIs "
        "released after the catalogs above were downloaded are not matched.",
        "4. Estimate a false-positive probability (for example with TRICERATOPS), which "
        "weighs the blends the centroid test cannot resolve.",
        "",
    ]
    return "\n".join(lines)
