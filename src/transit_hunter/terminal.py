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
import math
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
# The Unicode banner's 256-colour styles: the rows of the title, lighter at the top
# of each word, and its shadow; the star from its centre to its limb, and distant
# stars; the light curve and its dip.
_ANSI |= {f"title{i}": f"\x1b[38;5;{n}m" for i, n in enumerate((45, 39, 39, 33, 33, 27))}
_ANSI |= {f"limb{i}": f"\x1b[38;5;{n}m" for i, n in enumerate((220, 214, 208, 202))}
_ANSI |= {
    "shadow": "\x1b[38;5;244m",
    "sky": "\x1b[38;5;245m",
    "baseline": "\x1b[38;5;245m",
    "dip": "\x1b[38;5;214m",
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
# A star with a planet crossing it, the program's name, and below them the light
# curve with the dip that the crossing makes. The Unicode banner draws the star and
# the curve in braille characters, each a grid of 2 x 4 dots about as far apart
# across as down, so that a circle of dots looks round; the name is in block letters
# with a shadow of double lines. The ASCII banner is for terminals that cannot show
# those characters, or are too narrow for them.


def banner(version: str, color: bool = False, unicode: bool = True, width: int = 80) -> str:
    """The banner for a terminal ``width`` columns wide: in Unicode characters, or in
    ASCII if ``unicode`` is false or the Unicode banner would not fit."""
    if unicode and width > _UNICODE_WIDTH:
        return _unicode_banner(version, color)
    return _ascii_banner(version, color)


def _runs(cells: list[tuple[str, str | None]]) -> list[Segment]:
    """Characters and their styles, merged into runs of one style (spaces unstyled)."""
    segments: list[Segment] = []
    for char, style in cells:
        style = None if char == " " else style
        if segments and segments[-1][1] == style:
            segments[-1] = (segments[-1][0] + char, style)
        else:
            segments.append((char, style))
    return segments


_BRAILLE_BITS = ((0x01, 0x08), (0x02, 0x10), (0x04, 0x20), (0x40, 0x80))  # [dy][dx]


def _braille(dots: set[tuple[int, int]], columns: int, rows: int) -> list[str]:
    """Lines of braille characters showing the dots ``(x, y)``, 2 x 4 to a character."""

    def char(column: int, row: int) -> str:
        bits = sum(
            _BRAILLE_BITS[dy][dx]
            for dy in range(4)
            for dx in range(2)
            if (2 * column + dx, 4 * row + dy) in dots
        )
        return chr(0x2800 + bits) if bits else " "

    return ["".join(char(column, row) for column in range(columns)) for row in range(rows)]


# Block letters with a shadow of double lines, as in the "ANSI Shadow" FIGlet font.
_LETTERS = {
    "T": ("████████╗", "╚══██╔══╝", "   ██║   ", "   ██║   ", "   ██║   ", "   ╚═╝   "),
    "R": ("██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██║  ██║", "╚═╝  ╚═╝"),
    "A": (" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"),
    "N": ("███╗   ██╗", "████╗  ██║", "██╔██╗ ██║", "██║╚██╗██║", "██║ ╚████║", "╚═╝  ╚═══╝"),
    "S": ("███████╗", "██╔════╝", "███████╗", "╚════██║", "███████║", "╚══════╝"),
    "I": ("██╗", "██║", "██║", "██║", "██║", "╚═╝"),
    "H": ("██╗  ██╗", "██║  ██║", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"),
    "U": ("██╗   ██╗", "██║   ██║", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "),
    "E": ("███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "███████╗", "╚══════╝"),
}


def _word(word: str) -> list[str]:
    return ["".join(_LETTERS[letter][row] for letter in word) for row in range(6)]


_TRANSIT, _HUNTER = _word("TRANSIT"), _word("HUNTER")
_INDENT = len(_TRANSIT[0]) - len(_HUNTER[0])  # so that the words end in the same column
_TITLE = _TRANSIT + [" " * _INDENT + line for line in _HUNTER]
_TAGLINE = "planets in TESS light curves"

# The picture, and in it, in dots (x to the right, y down): the star's centre and
# radius, the planet's, and a few distant stars.
_PICTURE_COLUMNS, _PICTURE_ROWS = 22, len(_TITLE)
_STAR = (24.0, 24.0, 19.0)
_PLANET = (32.0, 27.5, 5.5)
_DISTANT_STARS = {(1, 2), (41, 1), (1, 27), (3, 41), (9, 46), (43, 45)}
_UNICODE_WIDTH = _PICTURE_COLUMNS + 1 + len(_TITLE[0])


def _picture() -> list[str]:
    """The star, a disc of dots, with the planet in front of it, a hole."""
    (sx, sy, sr), (px, py, pr) = _STAR, _PLANET
    dots = {
        (x, y)
        for x in range(2 * _PICTURE_COLUMNS)
        for y in range(4 * _PICTURE_ROWS)
        if (x + 0.5 - sx) ** 2 + (y + 0.5 - sy) ** 2 <= sr**2
        # the planet, with a dark ring that sets it off from the star
        and (x + 0.5 - px) ** 2 + (y + 0.5 - py) ** 2 > (pr + 1) ** 2
    }
    return _braille(dots | _DISTANT_STARS, _PICTURE_COLUMNS, _PICTURE_ROWS)


def _picture_style(column: int, row: int) -> str:
    """The star's colour darkens from its centre to its limb."""
    sx, sy, sr = _STAR
    distance = math.hypot(2 * column + 1 - sx, 4 * row + 2 - sy) / sr
    if distance > 1.1:
        return "sky"
    mu = math.sqrt(1 - min(distance, 1.0) ** 2)
    return f"limb{min(int(4.4 * (1 - mu)), 3)}"


def _transit_dip(z: float, k: float, u: float = 0.6) -> float:
    """The dip in the light curve, as a fraction of its depth, with a planet of radius
    ``k`` at ``z`` from the star's centre (both in stellar radii): straight ingress and
    egress, and a round bottom from limb darkening (coefficient ``u``)."""
    covered = min(max((1 + k - abs(z)) / (2 * k), 0.0), 1.0)
    return covered * (1 - u * (1 - math.sqrt(max(1 - z * z, 0.0))))


def _light_curve(columns: int) -> tuple[list[str], list[bool]]:
    """Three lines of light curve, flat but for a dip under the star as wide as 90% of
    it, and whether each column has part of the dip."""
    sx, _, sr = _STAR
    k = _PLANET[2] / sr
    dots, heights = set(), []
    for x in range(2 * columns):
        y = 1 + round(8 * _transit_dip((x + 0.5 - sx) * (1 + k) / (0.9 * sr), k))
        dots.add((x, y))
        if heights:  # join steep steps into a line
            dots.update((x, step) for step in range(min(y, heights[-1]) + 1, max(y, heights[-1])))
        heights.append(y)
    in_dip = [max(heights[2 * column : 2 * column + 2]) > 1 for column in range(columns)]
    return _braille(dots, columns, 3), in_dip


def _unicode_banner(version: str, color: bool) -> str:
    lines = []
    for row, (picture, title) in enumerate(zip(_picture(), _TITLE, strict=True)):
        cells = [(char, _picture_style(column, row)) for column, char in enumerate(picture)]
        cells.append((" ", None))
        cells += [(char, f"title{row % 6}" if char == "█" else "shadow") for char in title]
        lines.append(render(_runs(cells), color).rstrip())
    curve, in_dip = _light_curve(_UNICODE_WIDTH)
    for row, line in enumerate(curve):
        cells = [
            (char, "dip" if dip else "baseline") for char, dip in zip(line, in_dip, strict=True)
        ]
        segments = _runs(cells)
        if row == 1:  # the tagline beside the dip, under the name, and the version
            start = _PICTURE_COLUMNS + 1 + _INDENT
            room = _UNICODE_WIDTH - start - len(_TAGLINE) - len(version) - 1
            segments = [
                *_runs(cells[:start]),
                (_TAGLINE + " " * max(room, 2), None),
                (f"v{version}", "dim"),
            ]
        lines.append(render(segments, color).rstrip())
    return "\n".join(lines) + "\n"


# The ASCII banner. The disk is centred on column 22; so are the planet and the dip.
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
    """One row of the ASCII picture, split into styled runs."""
    cells: list[tuple[str, str | None]] = []
    for col, char in enumerate(_SKY[row]):
        if row >= 8:
            style = "curve"
        elif row == 4 and 21 <= col <= 23:
            style = "planet"
        elif row in _DISK_ROWS and col in _DISK_COLUMNS:
            style = "star"
        else:
            style = "dim"  # background stars
        cells.append((char, style))
    return _runs(cells)


def _ascii_banner(version: str, color: bool) -> str:
    """The ASCII picture, with the program's name and version beside the star."""
    beside = {
        3: (39, [("t r a n s i t - h u n t e r", "bold")]),
        4: (39, [(_TAGLINE, None)]),
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
