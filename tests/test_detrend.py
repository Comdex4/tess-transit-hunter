import numpy as np
import pytest

from transit_hunter.detrend import (
    DetrendConfig,
    _fill_trend,
    detrend,
    ephemeris_mask,
    plot_detrending,
    recommended_window,
)
from transit_hunter.models import transit_model
from transit_hunter.synthetic import NoiseModel, SyntheticPlanet, simulate_lightcurve
from transit_hunter.utils import robust_std, transit_mask


def _core_depth(lc, planet):
    """Mean depth over the flat bottom, relative to the out-of-transit median."""
    p = planet.to_params()
    core = transit_mask(lc.time, p.period, p.t0, 0.9 * p.t23)
    oot = ~transit_mask(lc.time, p.period, p.t0, 1.5 * p.t14)
    return np.median(lc.flux[oot]) - np.mean(lc.flux[core])


def test_flattening_removes_rotational_modulation():
    # A local-constant filter of width W leaves a residual ~A (1 - sinc(pi W / P)) of a
    # sinusoid with period P; for P_rot = 5 d (and its 2.5-d harmonic) and W = 0.5 d
    # that is well below the 200 ppm white noise.
    noise = NoiseModel(white_ppm=200, red_ppm=0, rotation_ppm=3000, rotation_period=5.0)
    lc = simulate_lightcurve(noise=noise, seed=21)
    assert robust_std(lc.flux) * 1e6 > 1500  # strongly variable before detrending
    flat = detrend(lc, DetrendConfig(window_length=0.5)).flat
    assert robust_std(flat.flux) * 1e6 == pytest.approx(200, rel=0.1)
    assert np.median(flat.flux) == pytest.approx(1.0, abs=2e-5)


def test_masking_preserves_transit_depth():
    planet = SyntheticPlanet(period=3.1, t0=2000.9, rp_rs=0.03, a_rs=10.0, b=0.2)
    noise = NoiseModel(white_ppm=100, red_ppm=0, rotation_ppm=2000, rotation_period=6.0)
    lc = simulate_lightcurve(noise=noise, planets=[planet], n_sectors=2, seed=22)
    truth = _core_depth(lc.with_flux(transit_model(lc.time, planet.to_params())), planet)

    config = DetrendConfig(window_length=0.75)
    unmasked = detrend(lc, config).flat
    mask = ephemeris_mask(lc.time, [(planet.period, planet.t0, planet.to_params().t14)])
    masked = detrend(lc, config, mask=mask)

    # Without a mask a shallow transit is partly absorbed into the trend
    # (roughly by T14/window); with the mask the depth is preserved.
    assert _core_depth(unmasked, planet) < 0.93 * truth
    assert _core_depth(masked.flat, planet) == pytest.approx(truth, rel=0.03)
    assert masked.mask.sum() == masked.flat.meta["detrend_masked_points"] > 0


def test_ephemeris_mask_accepts_tuples_and_objects():
    t = np.linspace(0, 20, 20001)
    planet = SyntheticPlanet(period=4.0, t0=1.0, rp_rs=0.05, a_rs=12.0)
    m1 = ephemeris_mask(t, [(4.0, 1.0, 0.1)], width_factor=2.0)
    assert m1.mean() == pytest.approx(0.2 / 4.0, rel=0.02)

    class Eph:
        period, t0, duration = 4.0, 1.0, 0.1

    np.testing.assert_array_equal(m1, ephemeris_mask(t, [Eph()], width_factor=2.0))
    both = ephemeris_mask(t, [(4.0, 1.0, 0.1), (planet.period, 2.0, 0.1)], width_factor=1.0)
    assert both.mean() == pytest.approx(2 * 0.1 / 4.0, rel=0.02)


def test_fill_trend_interpolates_within_segments():
    t = np.concatenate([np.arange(0, 1, 0.1), np.arange(5, 6, 0.1)])
    trend = np.linspace(1.0, 2.0, t.size)
    trend[3:5] = np.nan
    trend[12] = np.nan
    filled = _fill_trend(t, trend, max_gap=0.5)
    assert np.all(np.isfinite(filled))
    assert filled[3] == pytest.approx(np.linspace(1.0, 2.0, t.size)[3])


def test_detrend_rejects_unsupported_method(single_planet_lc):
    lc, _ = single_planet_lc
    with pytest.raises(ValueError):
        detrend(lc, DetrendConfig(method="savgol"))
    with pytest.raises(ValueError):
        detrend(lc, mask=np.zeros(3, dtype=bool))


def test_recommended_window():
    assert recommended_window(0.1) == pytest.approx(0.3)


def test_plot_detrending_writes_png(tmp_path, single_planet_lc):
    lc, _ = single_planet_lc
    result = detrend(lc)
    path = plot_detrending(result, tmp_path / "detrend.png", title="synthetic")
    assert path.exists() and path.stat().st_size > 10_000


def test_mask_aligned_with_input_even_with_nans(single_planet_lc):
    lc, planet = single_planet_lc
    flux = lc.flux.copy()
    flux[::97] = np.nan
    gappy = lc.with_flux(flux)
    mask = ephemeris_mask(gappy.time, [(planet.period, planet.t0, planet.to_params().t14)])
    result = detrend(gappy, mask=mask)
    assert len(result.flat) == np.isfinite(flux).sum()
    np.testing.assert_array_equal(result.mask, mask[np.isfinite(flux)])
