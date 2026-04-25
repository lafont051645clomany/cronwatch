"""Format dead-letter queue contents for CLI display."""
from __future__ import annotations

from typing import List

from cronwatch.deadletter import DeadLetter

_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def _fmt_dt(dt) -> str:
    return dt.strftime(_DATE_FMT) if dt else "—"


def _header() -> str:
    return (
        f"{'Job':<20} {'Queued At':<20} {'Attempts':>8}  {'Last Error'}"
    )


def _sep() -> str:
    return "-" * 72


def _row(dl: DeadLetter) -> str:
    error = (dl.last_error or "")[:30]
    return (
        f"{dl.job_name:<20} {_fmt_dt(dl.queued_at):<20}"
        f" {dl.attempts:>8}  {error}"
    )


def format_deadletter_table(letters: List[DeadLetter]) -> str:
    """Return a human-readable table of dead-letter entries."""
    if not letters:
        return "Dead-letter queue is empty."

    lines = [_header(), _sep()]
    for dl in letters:
        lines.append(_row(dl))
    lines.append(_sep())
    lines.append(f"{len(letters)} item(s) in queue.")
    return "\n".join(lines)
