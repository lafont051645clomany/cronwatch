"""Format RunGroup collections as human-readable tables."""
from __future__ import annotations

from typing import Dict, Sequence

from cronwatch.grouping import RunGroup

_COL_KEY = 24
_COL_COUNT = 8
_COL_FAIL = 8
_COL_RATE = 10
_COL_AVG = 12


def _header() -> str:
    return (
        f"{'Key':<{_COL_KEY}}"
        f"{'Runs':>{_COL_COUNT}}"
        f"{'Failures':>{_COL_FAIL}}"
        f"{'Success%':>{_COL_RATE}}"
        f"{'Avg dur(s)':>{_COL_AVG}}"
    )


def _sep() -> str:
    return "-" * (_COL_KEY + _COL_COUNT + _COL_FAIL + _COL_RATE + _COL_AVG)


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def _dur(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def _row(group: RunGroup) -> str:
    return (
        f"{group.key:<{_COL_KEY}}"
        f"{group.count:>{_COL_COUNT}}"
        f"{group.failure_count:>{_COL_FAIL}}"
        f"{_pct(group.success_rate):>{_COL_RATE}}"
        f"{_dur(group.avg_duration):>{_COL_AVG}}"
    )


def format_group_table(groups: Dict[str, RunGroup]) -> str:
    """Return a formatted table for *groups* sorted by key.

    Returns a short message when *groups* is empty.
    """
    if not groups:
        return "No groups to display."

    lines = [_header(), _sep()]
    for key in sorted(groups):
        lines.append(_row(groups[key]))
    return "\n".join(lines)
