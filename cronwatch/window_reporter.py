"""Format sliding-window statistics for CLI display."""
from __future__ import annotations

from typing import List, Optional

from cronwatch.window import WindowStats

_COL = (
    ("Job", 24),
    ("Samples", 9),
    ("Failures", 10),
    ("Fail%", 7),
    ("Avg(s)", 8),
    ("P95(s)", 8),
)


def _header() -> str:
    return "  ".join(f"{name:<{w}}" for name, w in _COL)


def _sep() -> str:
    return "  ".join("-" * w for _, w in _COL)


def _fmt(v: Optional[float], decimals: int = 1) -> str:
    return f"{v:.{decimals}f}" if v is not None else "—"


def _row(s: WindowStats) -> str:
    cols = [
        f"{s.job_name:<24}",
        f"{s.sample_count:<9}",
        f"{s.failure_count:<10}",
        f"{s.failure_rate * 100:<7.1f}",
        f"{_fmt(s.avg_duration):<8}",
        f"{_fmt(s.p95_duration):<8}",
    ]
    return "  ".join(cols)


def format_window_table(stats: List[WindowStats], window_minutes: int) -> str:
    if not stats:
        return "No data in window."
    lines = [
        f"Sliding window: last {window_minutes} minute(s)",
        _header(),
        _sep(),
    ]
    lines.extend(_row(s) for s in stats)
    return "\n".join(lines)
