import numpy as np
import pytest

from transit_hunter.detrend import DetrendConfig
from transit_hunter.inject import (
    CompletenessTable,
    Injection,
    InjectionGrid,
    RecoveryCriteria,
    completeness,
    completeness_markdown,
    draw_injections,
    inject,
    match_signal,
    plot_completeness,
    read_results,
    run_injections,
    run_one,
)
from transit_hunter.models import a_rs_from_mass_radius, t14
from transit_hunter.search import SearchConfig, Signal
from transit_hunter.synthetic import NoiseModel, simulate_lightcurve
from transit_hunter.utils import R_EARTH, R_SUN


@pytest.fixture(scope="module")
def base_lc():
    """One sector at 10-minute cadence: fast enough for end-to-end tests."""
    noise = NoiseModel(white_ppm=250, red_ppm=30, rotation_ppm=800, rotation_period=7.0)
    return simulate_lightcurve(noise=noise, n_sectors=1, cadence_minutes=10.0, seed=41)


def _injection(period=3.0, radius=6.0, t0=2001.0, b=0.2, index=0) -> Injection:
    """A specific planet around a Sun-like star."""
    rp_rs = radius * R_EARTH / R_SUN
    a_rs = a_rs_from_mass_radius(period, 1.0, 1.0)
    return Injection(
        index=index,
        period_bin=0,
        radius_bin=0,
        period=period,
        radius_earth=radius,
        t0=t0,
        b=b,
        rp_rs=rp_rs,
        a_rs=a_rs,
        duration=t14(period, a_rs, rp_rs, b),
        u1=0.4,
        u2=0.2,
    )


def test_grid_geometry():
    grid = InjectionGrid.log_spaced((0.5, 20.0), 8, (0.7, 8.0), 8, 32)
    assert grid.shape == (8, 8)
    assert grid.size == 2048
    assert grid.period_edges[0] == pytest.approx(0.5)
    ratios = np.diff(np.log(grid.radius_edges))
    assert np.allclose(ratios, ratios[0])


def test_draw_injections_fill_every_cell_reproducibly():
    grid = InjectionGrid.log_spaced((1.0, 10.0), 3, (1.0, 4.0), 2, 5)
    injections = draw_injections(grid, star_radius=0.8, star_mass=0.8, t_start=100.0, seed=7)
    assert len(injections) == grid.size == 30
    assert [i.index for i in injections] == list(range(30))
    for inj in injections:
        pe, re_ = grid.period_edges, grid.radius_edges
        assert pe[inj.period_bin] <= inj.period <= pe[inj.period_bin + 1]
        assert re_[inj.radius_bin] <= inj.radius_earth <= re_[inj.radius_bin + 1]
        assert 100.0 <= inj.t0 < 100.0 + inj.period
        assert 0.0 <= inj.b <= 0.9
        assert inj.duration > 0
    again = draw_injections(grid, 0.8, 0.8, 100.0, seed=7)
    assert [i.period for i in again] == [i.period for i in injections]


def test_inject_multiplies_transit(base_lc):
    inj = _injection(radius=10.0)
    out = inject(base_lc, inj)
    ratio = out.flux / base_lc.flux
    assert ratio.max() == pytest.approx(1.0)
    assert 1 - ratio.min() == pytest.approx(inj.rp_rs**2, rel=0.3)
    assert out.meta["injected"]["period"] == inj.period


def _signal(period, t0, detected=True):
    return Signal(
        iteration=1,
        period=period,
        t0=t0,
        duration=0.1,
        depth=1e-3,
        depth_err=1e-4,
        snr=20,
        snr_white=20,
        sde=12,
        power=1,
        n_transits=5,
        detected=detected,
    )


def test_match_signal_exact_alias_none():
    inj = _injection(period=4.0, t0=2001.0)
    assert match_signal(inj, _signal(4.02, 2001.0 + 3 * 4.0)) == "exact"
    assert match_signal(inj, _signal(4.0, 2001.0 + 0.3)) == "none"  # right period, wrong phase
    assert match_signal(inj, _signal(4.2, 2001.0)) == "none"  # 5 % off
    assert match_signal(inj, _signal(8.0, 2005.0)) == "alias"
    # Half period, signal epoch falling between two injected transits.
    assert match_signal(inj, _signal(2.0, 2003.0)) == "alias"


def test_run_one_recovers_large_and_misses_tiny(base_lc):
    cfg = SearchConfig(max_signals=2)
    big = run_one(
        _injection(period=3.1, radius=5.0, t0=2000.7),
        base_lc,
        DetrendConfig(),
        cfg,
        RecoveryCriteria(),
    )
    assert big["recovered"] and big["match"] == "exact"
    assert big["found_period"] == pytest.approx(3.1, rel=0.01)
    assert big["n_transits_in_data"] >= 7
    tiny = run_one(
        _injection(period=3.1, radius=0.3, t0=2000.7, index=1),
        base_lc,
        DetrendConfig(),
        cfg,
        RecoveryCriteria(),
    )
    assert not tiny["recovered"]


def test_run_injections_parallel_and_resume(tmp_path, base_lc):
    grid = InjectionGrid.log_spaced((1.5, 6.0), 2, (3.0, 8.0), 1, 2)
    injections = draw_injections(grid, 1.0, 1.0, base_lc.time[0], seed=3)
    out = tmp_path / "inj.csv"
    rows = run_injections(
        base_lc, injections, out, search_cfg=SearchConfig(max_signals=1), n_workers=2
    )
    assert len(rows) == 4
    assert {r["index"] for r in rows} == {0, 1, 2, 3}
    assert all(isinstance(r["recovered"], bool) for r in rows)
    first = out.read_text()
    # Resuming does no new work.
    rows2 = run_injections(
        base_lc, injections, out, search_cfg=SearchConfig(max_signals=1), n_workers=2
    )
    assert out.read_text() == first
    assert len(rows2) == 4
    assert read_results(out)[0].keys() == rows[0].keys()


def test_completeness_table_markdown_and_plot(tmp_path):
    grid = InjectionGrid.log_spaced((1.0, 10.0), 2, (1.0, 4.0), 2, 2)
    rows = []
    for i in range(2):
        for j in range(2):
            for k in range(2):
                rows.append(
                    {
                        "radius_bin": i,
                        "period_bin": j,
                        "recovered": (i + k) >= 1,
                        "match": "exact" if (i + k) >= 1 else "none",
                    }
                )
    table = completeness(rows, grid)
    assert isinstance(table, CompletenessTable)
    assert table.total.sum() == 8
    np.testing.assert_allclose(table.fraction, [[0.5, 0.5], [1.0, 1.0]])
    assert table.overall == pytest.approx(0.75)
    md = completeness_markdown(table)
    assert "100% (2/2)" in md and "50% (1/2)" in md
    assert md.count("\n") == 4  # header, separator, two radius rows
    path = plot_completeness(table, tmp_path / "c.png", title="test")
    assert path.exists() and path.stat().st_size > 10_000
    assert table.as_dict()["n_injections"] == 8


def test_injection_dataclass_roundtrip():
    inj = _injection()
    assert isinstance(inj, Injection)
    assert inj.params().period == inj.period
