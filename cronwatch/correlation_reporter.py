"""Format correlation results for CLI output."""
from __future__ import annotations

from typing import List

from cronwatch.correlation import CorrelationResult

_HDR = ("Anchor Job", "Related Job", "Overlapping Failures", "Window (s)")
_COL = (20, 20, 21, 12)


def _row(*cells: str) -> str:
    return "  ".join(str(c).ljust(w) for c, w in zip(cells, _COL))


def format_correlation_table(results: List[CorrelationResult]) -> str:
    if not results:
        return "No correlated failures found."

    sep = "  ".join("-" * w for w in _COL)
    lines = [_row(*_HDR), sep]
    for r in results:
        lines.append(
            _row(
                r.anchor_job,
                r.related_job,
                str(r.overlap_count),
                str(int(r.window_seconds)),
            )
        )
    return "\n".join(lines)
