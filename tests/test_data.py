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
