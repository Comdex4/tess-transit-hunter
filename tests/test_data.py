"""Tests for downloading/cleaning/caching. The network layer is replaced by fakes."""

import sys
import types

import astropy.units as u
import numpy as np
import pytest
from astropy.utils.masked import Masked

from transit_hunter import data
from transit_hunter.data import (
    BITMASKS,
    DEFAULT_BITMASK,
    QUALITY_FLAGS,
    CleaningConfig,
    NoDataError,
    SectorData,
    clean_sector,
    fetch_lightcurve,
    find_outliers,
    momentum_dumps,
    process_sectors,
    resolve_bitmask,
)
from transit_hunter.synthetic import (
    NoiseModel,
    RawSimulationOptions,
    SyntheticPlanet,
    simulate_lightcurve,
    simulate_raw_sectors,
)
from transit_hunter.utils import transit_mask


def test_bitmasks_match_lightkurve():
    lk_utils = pytest.importorskip("lightkurve.utils")
    flags = lk_utils.TessQualityFlags
    assert DEFAULT_BITMASK == flags.DEFAULT_BITMASK
    assert BITMASKS["hard"] == flags.HARD_BITMASK
    assert BITMASKS["hardest"] == flags.HARDEST_BITMASK


def test_resolve_bitmask():
    assert resolve_bitmask("default") == DEFAULT_BITMASK
    assert resolve_bitmask("NONE") == 0
    assert resolve_bitmask(5) == 5
    with pytest.raises(ValueError):
        resolve_bitmask("bogus")


@pytest.fixture(scope="module")
def raw_sectors():
    lc = simulate_lightcurve(
        noise=NoiseModel(white_ppm=300, red_ppm=0, rotation_ppm=800), n_sectors=2, seed=3
    )
    return simulate_raw_sectors(lc, RawSimulationOptions(outlier_rate=0.003), seed=4)


def test_clean_sector_applies_quality_mask_and_normalises(raw_sectors):
    raw = raw_sectors[0]
    lc, stats = clean_sector(raw)
    assert lc is not None
    # No cadence with a default-bitmask flag survives; benign flags are kept.
    kept = np.isin(raw.time, lc.time)
    assert not np.any(raw.quality[kept] & DEFAULT_BITMASK)
    benign = (raw.quality & QUALITY_FLAGS["ApertureCosmic"]) != 0
    assert np.any(kept & benign)
    assert np.all(np.isfinite(lc.flux)) and np.all(lc.flux_err > 0)
    assert np.median(lc.flux) == pytest.approx(1.0, abs=1e-3)
    assert stats["n_final"] == len(lc)
    assert stats["n_raw"] == raw.time.size
    removed = stats["n_quality_flagged"] + stats["n_nonfinite"] + stats["n_outliers"]
    assert stats["n_final"] == stats["n_raw"] - removed


def test_upper_outliers_removed_but_transit_kept():
    """Asymmetric clipping deletes positive spikes and keeps a deep transit intact."""
    planet = SyntheticPlanet(period=2.0, t0=2000.5, rp_rs=0.1, a_rs=7.0, b=0.2)
    noise = NoiseModel(white_ppm=300, red_ppm=0, rotation_ppm=0)
    lc = simulate_lightcurve(noise=noise, planets=[planet], seed=5)
    rng = np.random.default_rng(6)
    spikes = rng.choice(len(lc), 40, replace=False)
    spikes = spikes[~transit_mask(lc.time[spikes], 2.0, 2000.5, 0.2)]
    flux = lc.flux.copy()
    flux[spikes] += 0.01  # ~33 sigma cosmic rays
    outliers = find_outliers(lc.time, flux)
    assert set(spikes) <= set(np.flatnonzero(outliers))
    in_transit = transit_mask(lc.time, 2.0, 2000.5, 0.8 * planet.to_params().t14)
    assert not np.any(outliers & in_transit)
    # A symmetric clip would have destroyed the ~1% deep transit.
    symmetric = find_outliers(lc.time, flux, sigma_lower=4.0)
    assert np.mean(symmetric[in_transit]) > 0.5


def test_process_sectors_stitches_and_records_metadata(raw_sectors):
    lc = process_sectors(raw_sectors, tic_id=123)
    assert lc.sectors == [1, 2]
    assert np.all(np.diff(lc.time) > 0)
    assert lc.meta["tic_id"] == 123
    assert len(lc.meta["sector_stats"]) == 2
    assert lc.meta["stellar_header"]["teff"] == pytest.approx(5770.0)
    assert lc.meta["bitmask_value"] == DEFAULT_BITMASK


def test_process_sectors_rejects_tiny_sectors():
    tiny = SectorData(
        9, np.arange(10.0), np.ones(10), np.full(10, 1e-3), np.zeros(10, dtype=int), {"SECTOR": 9}
    )
    with pytest.raises(NoDataError):
        process_sectors([tiny], CleaningConfig(min_points=100))


def test_fetch_lightcurve_caches_to_disk(tmp_path, raw_sectors):
    calls = []

    def fake_downloader(tic_id, download_dir, sectors):
        calls.append((tic_id, sectors))
        return raw_sectors

    lc1 = fetch_lightcurve(42, cache_dir=tmp_path, downloader=fake_downloader)
    assert calls == [(42, None)]
    assert lc1.meta["loaded_from_cache"] is False
    lc2 = fetch_lightcurve(42, cache_dir=tmp_path, downloader=fake_downloader)
    assert len(calls) == 1, "second call must be served from the cache"
    assert lc2.meta["loaded_from_cache"] is True
    np.testing.assert_array_equal(lc1.time, lc2.time)
    np.testing.assert_array_equal(lc1.flux, lc2.flux)
    # A different cleaning configuration is a different cache entry.
    fetch_lightcurve(
        42, cache_dir=tmp_path, downloader=fake_downloader, config=CleaningConfig(sigma_upper=5.0)
    )
    assert len(calls) == 2
    fetch_lightcurve(42, cache_dir=tmp_path, downloader=fake_downloader, force_download=True)
    assert len(calls) == 3


class _FakeLC:
    """Mimics the attributes of a lightkurve LightCurve that data.py relies on."""

    def __init__(self, raw: SectorData, tic: int):
        self.time = types.SimpleNamespace(value=raw.time)
        mask = ~np.isfinite(raw.flux)
        self.flux = Masked(np.nan_to_num(raw.flux) * u.electron / u.s, mask=mask)
        self.flux_err = raw.flux_err * u.electron / u.s
        self.quality = Masked(raw.quality.astype(float), mask=np.zeros(raw.time.size, bool))
        self.meta = {
            "SECTOR": raw.sector,
            "TICID": tic,
            "TEFF": 3500.0,
            "RADIUS": 0.4,
            "CROWDSAP": 0.99,
        }


def test_download_spoc_sectors_parses_lightkurve_objects(monkeypatch, tmp_path, raw_sectors):
    requests = {}

    class FakeSearch:
        def __len__(self):
            return 3

        def download_all(self, **kwargs):
            requests["download"] = kwargs
            lcs = [_FakeLC(r, 77) for r in raw_sectors]
            lcs.append(_FakeLC(raw_sectors[0], 99999))  # a different target must be dropped
            return lcs

    def fake_search(target, **kwargs):
        requests["search"] = (target, kwargs)
        return FakeSearch()

    monkeypatch.setitem(
        sys.modules, "lightkurve", types.SimpleNamespace(search_lightcurve=fake_search)
    )
    out = data.download_spoc_sectors(77, tmp_path)
    target, kwargs = requests["search"]
    assert target == "TIC 77"
    assert kwargs["author"] == "SPOC" and kwargs["exptime"] == 120
    assert requests["download"]["flux_column"] == "pdcsap_flux"
    assert requests["download"]["quality_bitmask"] == "none"
    assert [s.sector for s in out] == [1, 2]
    # Masked flux values come back as NaN and are then removed by cleaning.
    assert np.isnan(out[0].flux).sum() == np.isnan(raw_sectors[0].flux).sum()
    assert out[0].header["TEFF"] == 3500.0
    lc = process_sectors(out, tic_id=77)
    assert lc.meta["stellar_header"]["radius"] == pytest.approx(0.4)


def test_download_raises_when_nothing_found(monkeypatch, tmp_path):
    class Empty:
        def __len__(self):
            return 0

    monkeypatch.setitem(
        sys.modules, "lightkurve", types.SimpleNamespace(search_lightcurve=lambda *a, **k: Empty())
    )
    with pytest.raises(NoDataError):
        data.download_spoc_sectors(1, tmp_path)


CUT_SHORT = (
    "This file may be corrupt due to an interrupted download. "
    "Please remove it from your disk and try again."
)


def test_download_replaces_a_file_cut_short_by_an_interrupted_download(
    monkeypatch, tmp_path, raw_sectors
):
    broken = tmp_path / "mastDownload" / "TESS" / "obs" / "obs_lc.fits"
    broken.parent.mkdir(parents=True)
    broken.write_bytes(b"SIMPLE  =")  # what a download stopped halfway leaves
    calls = []

    class FakeSearch:
        def __len__(self):
            return 2

        def download_all(self, **kwargs):
            calls.append(kwargs)
            if broken.exists():  # lightkurve reads the cached file, and fails
                raise RuntimeError(
                    f"Not recognized as a supported data product:\n{broken}\n{CUT_SHORT}"
                )
            return [_FakeLC(r, 77) for r in raw_sectors]

    monkeypatch.setitem(
        sys.modules,
        "lightkurve",
        types.SimpleNamespace(search_lightcurve=lambda *a, **k: FakeSearch()),
    )
    out = data.download_spoc_sectors(77, tmp_path)
    assert not broken.exists() and len(calls) == 2
    assert [s.sector for s in out] == [1, 2]


@pytest.mark.parametrize(
    "template",
    [  # lightkurve 2.6's three messages
        "Not recognized as a supported data product:\n{path}\n{cut}",
        "Unexpected error in detecting the type of the data product: 'IndexError: x'\n"
        "{path}\n{cut}",
        "Error in reading Data product {path} of type TessLightCurve .\n{cut}",
    ],
)
def test_cut_short_downloads_are_found_only_in_the_download_folder(tmp_path, template):
    cache = tmp_path / "cache"
    inside = cache / "mastDownload" / "TESS" / "obs" / "obs_lc.fits"
    outside = tmp_path / "elsewhere" / "obs_lc.fits"
    for path in (inside, outside):
        path.parent.mkdir(parents=True)
        path.write_bytes(b"")

    def error(path):
        return RuntimeError(template.format(path=path, cut=CUT_SHORT))

    assert data._cut_short_download(error(inside), cache) == inside
    assert data._cut_short_download(error(outside), cache) is None
    assert data._cut_short_download(error(f"{cache}/../elsewhere/obs_lc.fits"), cache) is None
    assert data._cut_short_download(RuntimeError(f"HTTP 503 for {inside}"), cache) is None


def test_lightkurve_names_a_cut_short_file_the_way_the_repair_expects(tmp_path):
    lk = pytest.importorskip("lightkurve")
    from astropy.io import fits

    path = tmp_path / "mastDownload" / "TESS" / "obs" / "obs_lc.fits"
    path.parent.mkdir(parents=True)
    fits.PrimaryHDU().writeto(path)
    path.write_bytes(path.read_bytes()[:100])  # cut short
    with pytest.raises(Exception) as error:
        lk.read(str(path))
    assert data._cut_short_download(error.value, tmp_path) == path


def test_cache_repair_gives_up_and_leaves_other_errors_alone(tmp_path):
    broken = tmp_path / "obs_lc.fits"
    calls = []

    def always_broken():
        calls.append(1)
        broken.write_bytes(b"")  # every download leaves a bad file again
        raise RuntimeError(f"Not recognized as a supported data product:\n{broken}\n{CUT_SHORT}")

    with pytest.raises(RuntimeError, match="may be corrupt"):
        data.download_with_cache_repair(always_broken, tmp_path, attempts=2)
    assert len(calls) == 3

    def unreachable():
        raise ConnectionError(f"MAST did not answer for {broken}")

    with pytest.raises(ConnectionError):
        data.download_with_cache_repair(unreachable, tmp_path)
    assert broken.exists()  # only a file an error calls cut short is deleted


def test_momentum_dumps_are_recorded_from_the_quality_flags(tmp_path, raw_sectors):
    time = 1500 + np.arange(0, 5, 2 / 1440)
    quality = np.zeros(time.size, dtype=np.int64)
    quality[1000:1003] |= QUALITY_FLAGS["Desat"]  # one dump flags a few cadences
    quality[2500] |= QUALITY_FLAGS["Desat"] | QUALITY_FLAGS["CoarsePoint"]
    quality[3000] |= QUALITY_FLAGS["CoarsePoint"]  # not a dump
    raw = SectorData(9, time, np.ones(time.size), np.full(time.size, 1e-3), quality)
    assert momentum_dumps(raw) == pytest.approx([time[1001], time[2500]])
    # The simulated sectors flag a dump every 3.1 days; all of them are recorded
    # (but those in the mid-sector gap, which flag no data), and they survive the
    # processed-data cache.
    lc = process_sectors(raw_sectors)
    expected = [
        t
        for r in raw_sectors
        for t in np.arange(r.time.min() + 1.0, r.time.max(), 3.1)
        if np.any(np.abs(r.time - t) < 5 / 1440)
    ]
    assert lc.meta["momentum_dumps"] == pytest.approx(sorted(expected), abs=2 / 1440)
    lc.save(tmp_path / "lc.npz")
    assert type(lc).load(tmp_path / "lc.npz").meta["momentum_dumps"] == lc.meta["momentum_dumps"]
