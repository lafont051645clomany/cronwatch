"""Format quota usage as a text table."""
from __future__ import annotations

from typing import Dict, List, Tuple

from cronwatch.quota import QuotaConfig, QuotaTracker

_COL = (20, 8, 8, 10, 10)


def _header() -> str:
    cols = ("Job", "Limit", "Period", "Used", "Remaining")
    row = "  ".join(c.ljust(_COL[i]) for i, c in enumerate(cols))
    sep = "  ".join("-" * w for w in _COL)
    return f"{row}\n{sep}"


def _row(job: str, cfg: QuotaConfig, used: int, remaining: int) -> str:
    cells = (
        job[:_COL[0]].ljust(_COL[0]),
        str(cfg.max_runs).ljust(_COL[1]),
        f"{cfg.period_seconds}s".ljust(_COL[2]),
        str(used).ljust(_COL[3]),
        str(remaining).ljust(_COL[4]),
    )
    return "  ".join(cells)


def format_quota_table(
    jobs: List[Tuple[str, QuotaConfig]],
    tracker: QuotaTracker,
) -> str:
    """Return a formatted quota-usage table for the given jobs."""
    if not jobs:
        return "No quota configurations found."
    lines = [_header()]
    for job, cfg in jobs:
        used = tracker.count(job, cfg)
        remaining = tracker.remaining(job, cfg)
        lines.append(_row(job, cfg, used, remaining))
    return "\n".join(lines)
