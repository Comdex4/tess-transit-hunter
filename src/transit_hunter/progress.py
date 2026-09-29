"""Progress reports from long-running steps.

The pipeline calls :func:`report` as it moves from stage to stage, as each chunk
of a BLS periodogram comes back and as the MCMC advances. Nothing happens unless a
listener is installed; the command-line interface installs one in an interactive
terminal (see :mod:`transit_hunter.terminal`). Reports are made from the main
process only, never from worker processes.

Events and their fields:

``stage``
    ``name`` (one of ``data``, ``detrend``, ``search``, ``fit`` and, at the end,
    ``done``), and optionally ``detail``, a short text.
``search_pass``
    ``iteration`` and ``max_iterations`` of the multi-planet search.
``bls``
    ``done`` and ``total`` chunks of the current periodogram.
``fit``
    ``n`` and ``total`` candidates, and ``period``.
``mcmc``
    ``step`` and ``max_steps`` (a chain may stop early once it converges).
``vet``
    ``n``, the candidate whose vetting starts.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

Listener = Callable[[str, dict[str, Any]], None]

_listeners: list[Listener] = []


def add_listener(listener: Listener) -> None:
    """Call ``listener(event, fields)`` for every report from now on."""
    _listeners.append(listener)


def remove_listener(listener: Listener) -> None:
    """Stop calling ``listener``; unknown listeners are ignored."""
    if listener in _listeners:
        _listeners.remove(listener)


def report(event: str, **fields: Any) -> None:
    """Pass an event to every listener (a no-op when there are none)."""
    for listener in list(_listeners):
        listener(event, fields)
