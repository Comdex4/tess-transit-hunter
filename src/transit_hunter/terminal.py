"""Terminal output of the command-line interface: a banner and a live progress line.

Both appear only on an interactive terminal, so logs, pipes and CI output stay
plain; ``--plain`` turns them off, and the ``NO_COLOR`` environment variable
(https://no-color.org) turns off colour alone. The progress line is redrawn when
the pipeline reports progress (:mod:`transit_hunter.progress`), never from a
timer thread: the pipeline forks worker processes, and forking a process that
runs other threads can deadlock the children.
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from collections.abc import Callable
from typing import Any, TextIO

_ANSI = {
    "dim": "\x1b[2m",
    "bold": "\x1b[1m",
    "star": "\x1b[33m",
    "planet": "\x1b[1;36m",
    "curve": "\x1b[36m",
    "done": "\x1b[32m",
    "now": "\x1b[1;33m",
}
_RESET = "\x1b[0m"

Segment = tuple[str, str | None]  # text and style name (None: no style)


def is_interactive(stream: TextIO) -> bool:
    """True if ``stream`` is a terminal a person is watching."""
    try:
        return bool(stream.isatty()) and os.environ.get("TERM") != "dumb"
    except (AttributeError, ValueError):
        return False


def use_color(stream: TextIO) -> bool:
    """Colour on an interactive terminal, unless ``NO_COLOR`` is set."""
    return is_interactive(stream) and "NO_COLOR" not in os.environ


def use_unicode(stream: TextIO) -> bool:
    """Whether the stream's encoding can show block and check-mark characters."""
    encoding = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
    return encoding.startswith("utf")


def render(segments: list[Segment], color: bool) -> str:
    """Join ``segments``, wrapping styled ones in ANSI codes when ``color``."""
    if not color:
        return "".join(text for text, _ in segments)
    return "".join(
        f"{_ANSI[style]}{text}{_RESET}" if style and text else text for text, style in segments
    )


# --------------------------------------------------------------------------- banner
# A star with a planet crossing it, and the light curve below with the dip that
# the crossing makes. The disk is centred on column 22; so are the planet and the dip.
_SKY = [
    "           .         *            .",
    "     *         .-'''''''''''-.",
    "            .'                 '.",
    "    .      /                     \\",
    "          |          (@)          |",
    "     *     \\                     /",
    "            '.                 .'",
    "      .        '-.._______..-'",
    "  " + "-" * 17 + "." + " " * 5 + "." + "-" * 22,
    " " * 20 + "\\___/",
]
_DISK_ROWS, _DISK_COLUMNS = range(1, 8), range(10, 35)


def _sky_segments(row: int) -> list[Segment]:
    """One row of the picture, split into styled runs."""
    text = _SKY[row]
    segments: list[Segment] = []
    for col, char in enumerate(text):
        if char == " ":
            style = None
        elif row >= 8:
            style = "curve"
        elif row == 4 and 21 <= col <= 23:
            style = "planet"
        elif row in _DISK_ROWS and col in _DISK_COLUMNS:
            style = "star"
        else:
            style = "dim"  # background stars
        if segments and segments[-1][1] == style:
            segments[-1] = (segments[-1][0] + char, style)
        else:
            segments.append((char, style))
    return segments


def banner(version: str, color: bool = False) -> str:
    """The picture, with the program's name and version beside the star."""
    beside = {
        3: (39, [("t r a n s i t - h u n t e r", "bold")]),
        4: (39, [("planets in TESS light curves", None)]),
        5: (39, [(f"v{version}", "dim")]),
        9: (28, [("<- a transit: the star dims", "dim")]),
    }
    lines = []
    for row in range(len(_SKY)):
        segments = _sky_segments(row)
        if row in beside:
            column, extra = beside[row]
            segments = [*segments, (" " * (column - len(_SKY[row])), None), *extra]
        lines.append(render(segments, color).rstrip())
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- progress
STAGES = ("data", "detrend", "search", "fit")
_LABELS = {"fit": "fit+vet"}


def _bar(fraction: float, width: int, unicode: bool) -> str:
    filled = round(max(0.0, min(1.0, fraction)) * width)
    full, empty = ("█", "░") if unicode else ("#", "-")
    return full * filled + empty * (width - filled) + f" {100 * fraction:3.0f}%"


def _clock(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


class ProgressLine:
    """A one-line view of the pipeline's progress, redrawn in place.

    Call the instance with progress events (it is a :mod:`transit_hunter.progress`
    listener). The line shows the stages done, the current one with its detail and
    step (BLS, MCMC, vetting), a bar of the step's work where one is known, and the
    elapsed time. An MCMC chain may stop before its maximum length once it converges,
    so its bar need not reach the end. Redraws are limited to ten a second, and
    events from any process other than the one that made the line (a forked worker)
    are ignored.
    """

    def __init__(
        self,
        stream: TextIO,
        color: bool = False,
        unicode: bool = True,
        clock: Callable[[], float] = time.monotonic,
        width: int | None = None,
    ) -> None:
        self.stream = stream
        self.color = color
        self.unicode = unicode
        self.clock = clock
        self.width = width
        self.started = clock()
        self.stage: str | None = None
        self.detail = ""
        self.step = ""
        self.fraction: float | None = None
        self.done: list[str] = []
        self._pid = os.getpid()
        self._last = float("-inf")
        self._shown = False

    # a progress listener
    def __call__(self, event: str, fields: dict[str, Any]) -> None:
        if os.getpid() != self._pid:
            return
        if event == "stage" and fields["name"] == "data":
            # A download may print its own progress, so this stage gets a plain line.
            self.stage = "data"
            detail = fields.get("detail") or "loading the light curve"
            self.stream.write(render([(f"  {detail}", "dim")], self.color) + "\n")
            self.stream.flush()
            return
        force = True
        if event == "stage":
            name = fields["name"]
            if self.stage and self.stage not in self.done:
                self.done.append(self.stage)
            self.stage = None if name == "done" else name
            self.detail, self.step, self.fraction = fields.get("detail", ""), "", None
        elif event == "search_pass":
            self.detail = f"pass {fields['iteration']} of up to {fields['max_iterations']}"
            self.step, self.fraction = "", None
        elif event == "bls":
            self.step, self.fraction = "BLS", fields["done"] / max(fields["total"], 1)
            force = False
        elif event == "fit":
            n, total = fields["n"], fields["total"]
            self.detail = f"candidate {n} of {total}, P = {fields['period']:.4g} d"
            self.step, self.fraction = "", None
        elif event == "mcmc":
            self.step, self.fraction = "MCMC", fields["step"] / max(fields["max_steps"], 1)
            force = False
        elif event == "vet":
            self.step, self.fraction = "vetting", None
        self.draw(force=force)

    def segments(self) -> list[Segment]:
        mark_done, mark_now, mark_todo, sep = (
            ("✓", "▶", "·", " │ ") if self.unicode else ("[x]", "[>]", "[ ]", " | ")
        )
        parts: list[Segment] = [("  ", None)]
        for name in STAGES:
            label = _LABELS.get(name, name)
            if name in self.done:
                parts.append((f"{mark_done}{label} ", "done"))
            elif name == self.stage:
                parts.append((f"{mark_now}{label} ", "now"))
            else:
                parts.append((f"{mark_todo}{label} ", "dim"))
        elapsed = _clock(self.clock() - self.started)
        if self.stage is None and self.done:
            parts.append((f"{sep}done in {elapsed}", "done"))
            return parts
        if self.detail:
            parts.append((f"{sep}{self.detail}", None))
        if self.step:
            parts.append((f"  {self.step}", "bold"))
        if self.fraction is not None:
            parts.append((" " + _bar(self.fraction, 16, self.unicode), "curve"))
        parts.append((f"{sep}{elapsed}", "dim"))
        return parts

    def text(self) -> str:
        """The current line, cut to the terminal's width."""
        width = self.width or shutil.get_terminal_size((100, 20)).columns
        room, kept = max(width - 1, 10), []
        for text, style in self.segments():
            if room <= 0:
                break
            kept.append((text[:room], style))
            room -= len(text)
        return render(kept, self.color)

    def draw(self, force: bool = False) -> None:
        now = self.clock()
        if not force and now - self._last < 0.1:
            return
        self._last = now
        self.stream.write("\r" + self.text() + "\x1b[K")
        self.stream.flush()
        self._shown = True

    def newline(self) -> None:
        """End the current line, so that other output starts on its own line."""
        if self._shown:
            self.stream.write("\n")
            self.stream.flush()
            self._shown = False

    def clear(self) -> None:
        """Erase the line (before printing something else in its place)."""
        if self._shown:
            self.stream.write("\r\x1b[K")
            self.stream.flush()
            self._shown = False

    def finish(self) -> None:
        """Draw the final state and move to the next line."""
        if self.stage and self.stage not in self.done:
            self.done.append(self.stage)
        self.stage, self.detail, self.step, self.fraction = None, "", "", None
        self.draw(force=True)
        self.newline()


class ProgressLogHandler(logging.Handler):
    """Print log records on their own lines without breaking the progress line."""

    def __init__(self, line: ProgressLine, level: int = logging.WARNING) -> None:
        super().__init__(level)
        self.line = line
        self.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            self.line.clear()
            self.line.stream.write(message + "\n")
            self.line.draw(force=True)
        except Exception:  # logging must never raise
            self.handleError(record)
