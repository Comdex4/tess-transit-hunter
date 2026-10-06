"""The centroid test on synthetic target pixels: is the dip on the target?"""

from __future__ import annotations

import math

import numpy as np
import pytest
from astropy.wcs import WCS

from transit_hunter.centroid import (
    _chi2_2dof,
    centroid_test,
    measure_centroid,
    plot_centroid,
    significance,
)
from transit_hunter.lightcurve import LightCurve
from transit_hunter.pixels import (
    Neighbour,
    PixelData,
    PixelSource,
    PRFModel,
    btjd_to_year,
    propagate,
)
from transit_hunter.utils import fold
from transit_hunter.vet import FAIL, NA, PASS, VetConfig, decide, run_vetting

RA, DEC = 150.0, -30.0
PERIOD, T0, DURATION = 2.0, 1401.3, 0.12
TARGET_TIC, NEIGHBOUR_TIC = 111, 222
NEIGHBOUR_NORTH = 42.0  # arcsec, two pixels


def _wcs() -> WCS:
    """TAN projection with 21-arcsec pixels, north up (+row) and east left (-column)."""
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [RA, DEC]
    w.wcs.crpix = [6.0, 6.0]  # 1-based: the target sits on pixel (5, 5)
    w.wcs.cdelt = [-21.0 / 3600, 21.0 / 3600]
    return w


def _pixels(dip_on: str, depth: float, sector: int = 5, seed: int = 0) -> PixelData:
    """Ten days of an 11 x 11 stamp: the target at (5, 5), a fainter star 2 pixels north."""
    rng = np.random.default_rng(seed)
    time = np.arange(1400.0, 1410.0, 2.0 / 1440.0)
    prf = PRFModel.gaussian(0.8)
    shape = (11, 11)
    stars = {"target": ((5.0, 5.0), 10000.0), "neighbour": ((5.0, 7.0), 2000.0)}
    inside = np.abs(fold(time, PERIOD, T0)) < DURATION / 2
    flux = np.full((time.size, *shape), 50.0, dtype=np.float32)
    for name, ((x, y), total) in stars.items():
        level = np.ones(time.size)
        if name == dip_on:
            level[inside] -= depth
        flux += (level[:, None, None] * (total * prf.model(x, y, shape))[None]).astype(np.float32)
    flux += rng.normal(0.0, 20.0, flux.shape).astype(np.float32)
    target_image = prf.model(5.0, 5.0, shape)
    return PixelData(
        sector=sector,
        camera=1,
        ccd=1,
        column=100,
        row=100,
        time=time,
        flux=flux,
        wcs=_wcs(),
        ra=RA,
        dec=DEC,
        tmag=10.0,
        aperture=target_image > 0.02 * target_image.max(),
    )


def _neighbours(ra: float, dec: float) -> list[Neighbour]:
    return [
        Neighbour(TARGET_TIC, RA, DEC, 10.0),
        Neighbour(NEIGHBOUR_TIC, RA, DEC + NEIGHBOUR_NORTH / 3600, 11.75),
    ]


def _source(*pixels: PixelData) -> PixelSource:
    return PixelSource(
        TARGET_TIC,
        data=pixels,
        prf_loader=lambda p: PRFModel.gaussian(0.8),
        neighbour_loader=_neighbours,
    )


def _light_curve(pixels: PixelData) -> LightCurve:
    """Aperture photometry of the synthetic stamp, normalized."""
    raw = pixels.flux[:, pixels.aperture].sum(axis=1).astype(float)
    flux = raw / np.median(raw)
    err = np.full(flux.size, float(np.std(flux[np.abs(fold(pixels.time, PERIOD, T0)) > DURATION])))
    return LightCurve(pixels.time, flux, err, np.full(flux.size, pixels.sector))


def _measure(pixels: PixelData, lc: LightCurve | None = None, depth: float = 0.01):
    cfg = VetConfig()
    return measure_centroid(
        _source(pixels),
        lc or _light_curve(pixels),
        PERIOD,
        T0,
        DURATION,
        depth,
        cfg.centroid_floor_arcsec,
        cfg.centroid_min_snr,
        cfg.centroid_max_sectors,
    )


def test_prf_model_is_normalised_and_centred():
    prf = PRFModel.gaussian(0.8)
    image = prf.model(5.3, 4.6, (11, 11))
    assert image.sum() == pytest.approx(1.0, abs=1e-3)
    yy, xx = np.mgrid[0:11, 0:11]
    assert (image * xx).sum() / image.sum() == pytest.approx(5.3, abs=0.02)
    assert (image * yy).sum() / image.sum() == pytest.approx(4.6, abs=0.02)


def test_significance_uses_gaussian_equivalent_levels():
    assert _chi2_2dof(3.0) == pytest.approx(11.83, abs=0.01)
    assert significance(np.array([math.sqrt(11.829), 0.0]), np.eye(2)) == pytest.approx(
        3.0, abs=1e-3
    )
    assert significance(np.array([0.0, 0.0]), np.eye(2)) == pytest.approx(0.0, abs=1e-6)


def test_proper_motion_moves_the_target_to_the_observing_epoch():
    # one arcsec per year northwards, observed twenty years after the TIC epoch
    ra, dec = propagate(RA, DEC, 0.0, 1000.0, 2020.0)
    assert ra == pytest.approx(RA)
    assert (dec - DEC) * 3600 == pytest.approx(20.0)
    assert btjd_to_year(1400.0) == pytest.approx(2018.768, abs=0.001)  # 2018 October 8
    pixels = _pixels("target", 0.01)
    pixels.pmdec = 1000.0 * 21.0 / (pixels.epoch - 2000.0)  # one pixel north by then
    x, y = pixels.target_pixel()
    assert x == pytest.approx(5.0, abs=1e-6)
    assert y == pytest.approx(6.0, abs=1e-3)


def test_a_dip_on_the_target_passes():
    measurement = _measure(_pixels("target", 0.01))
    test = centroid_test(measurement, 3.0)
    assert test.status == PASS, test.message
    assert measurement.separation < 2.0
    sector = measurement.sectors[0]
    assert sector.n_transits == 5
    assert sector.noise_from.startswith("the scatter of the 5 transits")
    assert "from the target" in test.message


def test_a_dip_on_a_neighbour_fails_and_names_it():
    pixels = _pixels("neighbour", 0.3)
    measurement = _measure(pixels, depth=0.005)
    test = centroid_test(measurement, 3.0)
    assert test.status == FAIL, test.message
    east, north = measurement.offset
    assert north == pytest.approx(NEIGHBOUR_NORTH, abs=3.0)
    assert abs(east) < 3.0
    assert f"TIC {NEIGHBOUR_TIC}" in test.message
    assert test.details["neighbours"][0]["tic_id"] == NEIGHBOUR_TIC


def test_only_the_light_curves_transits_are_used():
    # a transit left out of the light curve (as the pipeline does with a bad one)
    # is left out of the difference images too
    pixels = _pixels("target", 0.01)
    lc = _light_curve(pixels)
    first = np.abs(lc.time - T0) < DURATION
    measurement = _measure(pixels, lc.select(~first))
    assert measurement.sectors[0].n_transits == 4


def test_unavailable_pixels_make_the_test_na_and_the_verdict_a_caveat():
    pixels = _pixels("target", 0.01)
    source = PixelSource.unavailable("target pixels not requested (--no-pixels)")
    cfg = VetConfig()
    measurement = measure_centroid(
        source, _light_curve(pixels), PERIOD, T0, DURATION, 0.01, 2.5, 4.0, 4
    )
    test = centroid_test(measurement, cfg.centroid_sigma)
    assert test.status == NA
    assert "--no-pixels" in test.message
    verdict, reasons = decide([test])
    assert verdict == "planet candidate (with caveats)"
    assert any("not tested: centroid" in r for r in reasons)


def test_a_dip_too_shallow_for_the_pixels_is_na():
    measurement = _measure(_pixels("target", 0.00005))
    test = centroid_test(measurement, 3.0)
    assert test.status == NA
    assert "not detected" in test.message


def test_run_vetting_adds_the_centroid_test_only_with_a_pixel_source(tmp_path):
    pixels = _pixels("neighbour", 0.3)
    lc = _light_curve(pixels)
    without = run_vetting(lc, PERIOD, T0, DURATION, depth=0.005)
    assert "centroid" not in [t.name for t in without.tests]
    report = run_vetting(lc, PERIOD, T0, DURATION, depth=0.005, pixels=_source(pixels))
    assert report.test("centroid").status == FAIL
    assert report.verdict == "likely false positive"
    path = plot_centroid(report.centroid, report.test("centroid"), tmp_path / "centroid.png", "x")
    assert path is not None and path.stat().st_size > 10_000
