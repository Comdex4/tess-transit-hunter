"""The command-line interface's banner and live progress line, and the progress hook."""

import io
import logging
import re
import sys

import numpy as np
import pytest

from transit_hunter import cli, progress
from transit_hunter.fit import FitConfig, fit_transit
from transit_hunter.lightcurve import LightCurve
from transit_hunter.models import TransitParams, transit_model
from transit_hunter.search import SearchConfig, iterative_search
from transit_hunter.synthetic import tess_timestamps
from transit_hunter.terminal import ProgressLine, ProgressLogHandler, banner

ANSI = re.compile(r"\x1b\[[0-9;]*m")


class FakeTerminal(io.StringIO):
    """A text stream that says it is a terminal."""

    encoding = "utf-8"

    def isatty(self):
        return True


def test_banner_draws_a_transit_in_plain_text():
    art = banner("1.2.3")
    assert "\x1b[" not in art
    assert "(@)" in art  # the planet on the star's disk
    assert "\\___/" in art  # the dip it makes in the light curve
    assert "t r a n s i t - h u n t e r" in art and "v1.2.3" in art
    assert max(len(line) for line in art.splitlines()) <= 79


def test_banner_colour_only_adds_escape_codes():
    coloured = banner("1.2.3", color=True)
    assert "\x1b[" in coloured
    assert ANSI.sub("", coloured) == banner("1.2.3")


def test_progress_reports_reach_listeners_only_while_installed():
    seen = []

    def listener(event, fields):
        seen.append((event, fields))

    progress.report("stage", name="search")  # nobody is listening: nothing happens
    progress.add_listener(listener)
    try:
        progress.report("bls", done=3, total=10)
    finally:
        progress.remove_listener(listener)
    progress.report("bls", done=4, total=10)
    assert seen == [("bls", {"done": 3, "total": 10})]


def test_progress_line_follows_stages_steps_and_bars():
    now = [0.0]
    stream = io.StringIO()
    line = ProgressLine(stream, clock=lambda: now[0], width=140)
    line("stage", {"name": "data", "detail": "TIC 1: loading the light curve"})
    assert stream.getvalue() == "  TIC 1: loading the light curve\n"  # a plain line
    line("stage", {"name": "detrend", "detail": "19,000 points"})
    line("stage", {"name": "search"})
    line("search_pass", {"iteration": 2, "max_iterations": 5})
    now[0] = 75.0
    line("bls", {"done": 1, "total": 4})
    text = line.text()
    assert "✓data" in text and "✓detrend" in text and "▶search" in text and "·fit+vet" in text
    assert "pass 2 of up to 5" in text and "BLS" in text and "25%" in text and "1:15" in text

    line("stage", {"name": "fit"})
    line("fit", {"n": 1, "total": 2, "period": 3.36})
    line("mcmc", {"step": 5000, "max_steps": 20000})
    text = line.text()
    assert "✓search" in text and "candidate 1 of 2, P = 3.36 d" in text
    assert "MCMC" in text and "25%" in text
    line("vet", {"n": 1})
    assert "vetting" in line.text() and "%" not in line.text()  # no bar while vetting

    line("stage", {"name": "done"})
    line.finish()
    assert "✓fit+vet" in line.text() and "done in 1:15" in line.text()
    assert stream.getvalue().endswith("\n")


def test_progress_line_on_a_narrow_ascii_terminal():
    line = ProgressLine(io.StringIO(), unicode=False, clock=lambda: 0.0, width=40)
    line("stage", {"name": "search"})
    line("bls", {"done": 1, "total": 2})
    text = line.text()
    assert text.startswith("  [ ]data [ ]detrend [>]search")
    assert len(text) <= 39


def test_progress_line_ignores_forked_workers(monkeypatch):
    line = ProgressLine(io.StringIO(), clock=lambda: 0.0, width=100)
    monkeypatch.setattr("os.getpid", lambda: -1)  # as seen from another process
    line("stage", {"name": "search"})
    assert line.stage is None


def test_warnings_print_above_the_progress_line():
    stream = io.StringIO()
    line = ProgressLine(stream, clock=lambda: 0.0, width=100)
    line("stage", {"name": "search"})
    logger = logging.getLogger("transit_hunter.test_terminal")
    handler = ProgressLogHandler(line)
    logger.addHandler(handler)
    try:
        logger.warning("a sector was rejected")
    finally:
        logger.removeHandler(handler)
    out = stream.getvalue()
    # The line is erased, the warning printed on its own line, and the line redrawn.
    warning = "\r\x1b[KWARNING transit_hunter.test_terminal: a sector was rejected\n"
    assert warning in out
    assert out.endswith("\r" + line.text() + "\x1b[K")


def _fake_pipeline(lc, outdir, stellar, config, name):
    progress.report("stage", name="detrend", detail=f"{len(lc):,} points")
    progress.report("stage", name="search")
    progress.report("search_pass", iteration=1, max_iterations=config.search.max_signals)
    progress.report("bls", done=1, total=1)
    progress.report("stage", name="done")
    return {"target": {"name": name}, "search": {"n_detections": 0}, "planets": []}


def test_cli_shows_the_banner_and_progress_on_a_terminal(monkeypatch, tmp_path, capsys):
    terminal = FakeTerminal()
    monkeypatch.setattr(sys, "stderr", terminal)
    monkeypatch.setenv("TERM", "xterm")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr(cli, "run_on_lightcurve", _fake_pipeline)
    assert cli.main(["demo", "--sectors", "1", "--outdir", str(tmp_path)]) == 0
    shown = terminal.getvalue()
    assert "(@)" in shown and "t r a n s i t - h u n t e r" in shown
    assert "\x1b[1" not in shown and "\x1b[3" not in shown  # NO_COLOR: no colour codes
    assert "  simulating a three-planet system\n" in shown
    assert "✓data" in shown and "▶search" in shown and "done in" in shown
    # The summary still goes to standard output, after the progress line has ended.
    assert "Synthetic M-dwarf system: 0 detection(s)" in capsys.readouterr().out
    assert shown.endswith("\n")
    assert not any(isinstance(h, ProgressLogHandler) for h in logging.getLogger().handlers)


@pytest.mark.parametrize(
    "argv, interactive",
    [
        (["demo", "--plain"], True),
        (["demo", "-v"], True),
        (["demo"], False),
    ],
)
def test_cli_stays_plain(monkeypatch, tmp_path, capsys, argv, interactive):
    stream = FakeTerminal() if interactive else io.StringIO()
    monkeypatch.setattr(sys, "stderr", stream)
    monkeypatch.setenv("TERM", "xterm")
    monkeypatch.setattr(cli, "run_on_lightcurve", _fake_pipeline)
    assert cli.main([*argv, "--sectors", "1", "--outdir", str(tmp_path)]) == 0
    assert "(@)" not in stream.getvalue() and "done in" not in stream.getvalue()
    assert "0 detection(s)" in capsys.readouterr().out


def test_search_and_fit_report_their_progress():
    time, sector = tess_timestamps(1, cadence_minutes=2.0, start=2000.0)
    params = TransitParams(t0=2003.2, period=3.7, rp_rs=0.08, a_rs=11.0, b=0.35, u1=0.45, u2=0.2)
    rng = np.random.default_rng(1)
    flux = transit_model(time, params) + rng.normal(0, 300e-6, time.size)
    lc = LightCurve(time, flux, np.full(time.size, 300e-6), sector)
    events = []

    def listener(event, fields):
        events.append((event, fields))

    progress.add_listener(listener)
    try:
        config = SearchConfig(max_signals=1, n_workers=1, stellar_density=1.0)
        result = iterative_search(lc, config)
        sig = result.signals[0]
        fit_config = FitConfig(n_walkers=24, max_steps=300, min_steps=200, check_interval=100)
        fit_transit(lc, sig.period, sig.t0, sig.duration, sig.depth, config=fit_config)
    finally:
        progress.remove_listener(listener)
    names = [e for e, _ in events]
    assert names[0] == "search_pass" and events[0][1]["iteration"] == 1
    bls = [f for e, f in events if e == "bls"]
    assert bls and bls[-1]["done"] == bls[-1]["total"]
    steps = [f["step"] for e, f in events if e == "mcmc"]
    assert steps and steps == sorted(steps) and all(s % 100 == 0 for s in steps)
    assert all(f["max_steps"] == 300 for e, f in events if e == "mcmc")
