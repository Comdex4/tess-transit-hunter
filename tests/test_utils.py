import json
import math

import numpy as np
import pytest

from transit_hunter.lightcurve import LightCurve
from transit_hunter.utils import (
    bin_timeseries,
    binned_rms,
    epoch_index,
    fold,
    robust_std,
    running_median,
    segment_bounds,
    to_jsonable,
    transit_mask,
)


def test_fold_is_centred_on_transit():
    t = np.array([10.0, 10.4, 12.0, 13.9, 14.1])
    phase = fold(t, period=2.0, t0=10.0)
    assert phase == pytest.approx([0.0, 0.4, 0.0, -0.1, 0.1])
    assert np.all((phase >= -1.0) & (phase < 1.0))


def test_transit_mask_and_epochs():
    t = np.linspace(0.0, 10.0, 10001)
    mask = transit_mask(t, period=2.5, t0=1.0, duration=0.2)
    # Duty cycle = duration / period.
    assert mask.mean() == pytest.approx(0.2 / 2.5, rel=0.02)
    assert set(epoch_index(t[mask], 2.5, 1.0)) == {0, 1, 2, 3}


def test_robust_std_ignores_outliers(rng):
    x = rng.normal(0.0, 2.0, 20000)
    x[:200] += 100.0
    assert robust_std(x) == pytest.approx(2.0, rel=0.05)
    assert math.isnan(robust_std(np.array([np.nan])))


def test_bin_timeseries_weighted_mean():
    x = np.array([0.1, 0.2, 1.1, 1.2])
    y = np.array([1.0, 3.0, 5.0, 5.0])
    err = np.array([1.0, 1.0, 1.0, 2.0])
    xb, yb, eb, n = bin_timeseries(x, y, err, width=1.0)
    assert n.tolist() == [2, 2]
    assert yb[0] == pytest.approx(2.0)
    assert eb[0] == pytest.approx(1 / math.sqrt(2))
    assert xb[1] == pytest.approx(1.15)
    # Unweighted: standard error of the mean.
    _, yb2, eb2, _ = bin_timeseries(x, y, width=1.0)
    assert yb2[0] == pytest.approx(2.0)
    assert eb2[0] == pytest.approx(np.std([1.0, 3.0], ddof=1) / math.sqrt(2))


def test_bin_timeseries_with_edges_drops_outside():
    x = np.array([-1.0, 0.5, 1.5, 9.0])
    y = np.ones(4)
    xb, _, _, n = bin_timeseries(x, y, edges=np.array([0.0, 1.0, 2.0]))
    assert xb.tolist() == [0.5, 1.5]
    assert n.tolist() == [1, 1]


def test_binned_rms_white_noise_scales_as_root_n(rng):
    cadence = 2.0 / 1440
    t = np.arange(0, 27.0, cadence)
    f = rng.normal(0.0, 1e-3, t.size)
    width = 1.0 / 24  # 1 hour = 30 points
    assert binned_rms(t, f, width) == pytest.approx(1e-3 / math.sqrt(30), rel=0.1)


def test_binned_rms_detects_red_noise(rng):
    cadence = 2.0 / 1440
    t = np.arange(0, 27.0, cadence)
    white = rng.normal(0.0, 1e-3, t.size)
    red = 1e-3 * np.sin(2 * np.pi * t / 0.5)  # 12-hour correlated signal
    width = 1.0 / 24
    assert binned_rms(t, white + red, width) > 2 * binned_rms(t, white, width)


def test_segment_bounds_and_running_median():
    t = np.concatenate([np.arange(0, 5, 0.01), np.arange(10, 15, 0.01)])
    assert segment_bounds(t, max_gap=1.0) == [(0, 500), (500, 1000)]
    # A step between segments must not leak across the gap.
    v = np.where(t < 7, 1.0, 2.0)
    med = running_median(t, v, window=2.0)
    assert np.all(med[t < 7] == 1.0)
    assert np.all(med[t > 7] == 2.0)


def test_to_jsonable_strict():
    obj = {"a": np.float64(1.5), "b": np.array([1, 2]), "c": float("nan"), "d": (np.int64(3),)}
    out = to_jsonable(obj)
    assert json.loads(json.dumps(out, allow_nan=False)) == {
        "a": 1.5,
        "b": [1, 2],
        "c": None,
        "d": [3],
    }


def test_lightcurve_sorts_selects_and_roundtrips(tmp_path, rng):
    t = rng.uniform(0, 10, 100)
    lc = LightCurve(t, np.ones(100), np.full(100, 1e-3), np.ones(100, dtype=int), {"k": 1})
    assert np.all(np.diff(lc.time) >= 0)
    sub = lc.select(lc.time < 5)
    assert len(sub) == int(np.sum(t < 5))
    path = lc.save(tmp_path / "lc.npz")
    back = LightCurve.load(path)
    np.testing.assert_array_equal(back.time, lc.time)
    assert back.meta == {"k": 1}
    assert back.sectors == [1]


def test_lightcurve_bin_reduces_errors():
    t = np.arange(0, 1, 2 / 1440)
    lc = LightCurve(t, np.ones(t.size), np.full(t.size, 1e-3))
    binned = lc.bin(10 / 1440)
    assert len(binned) == pytest.approx(len(lc) / 5, abs=1)
    assert np.median(binned.flux_err) == pytest.approx(1e-3 / math.sqrt(5), rel=1e-6)


def test_lightcurve_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        LightCurve(np.arange(3), np.ones(2), np.ones(3))
