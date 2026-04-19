"""Format throttle state as a human-readable table."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from cronwatch.throttle import ThrottleConfig, Throttler

_COL = (20, 10, 10)


def _header() -> str:
    return (
        f"{'Job':<{_COL[0]}} {'Alerts':>{_COL[1]}} {'Allowed':>{_COL[2]}}"
    )


def _sep() -> str:
    return "-" * (_COL[0] + _COL[1] + _COL[2] + 2)


def _row(job: str, count: int, allowed: bool) -> str:
    flag = "yes" if allowed else "NO"
    return f"{job:<{_COL[0]}} {count:>{_COL[1]}} {flag:>{_COL[2]}}"


def format_throttle_table(
    throttler: Throttler,
    job_names: List[str],
    at: datetime | None = None,
) -> str:
    """Return a table showing current throttle counts for each job."""
    if not job_names:
        return "No jobs to display."
    now = at or datetime.now(timezone.utc)
    lines = [_header(), _sep()]
    for name in sorted(job_names):
        count = throttler.current_count(name, at=now)
        allowed = throttler.is_allowed(name, at=now)
        lines.append(_row(name, count, allowed))
    return "\n".join(lines)
