"""Format watchdog violations as a human-readable table."""
from __future__ import annotations

from typing import List

from cronwatch.watchdog import WatchdogViolation

_COL_JOB = 24
_COL_LAST = 26
_COL_SILENCE = 12
_COL_THRESH = 12


def _header() -> str:
    return (
        f"{'Job':<{_COL_JOB}} "
        f"{'Last Seen':<{_COL_LAST}} "
        f"{'Silence(s)':>{_COL_SILENCE}} "
        f"{'Threshold(s)':>{_COL_THRESH}}"
    )


def _sep() -> str:
    return "-" * (_COL_JOB + _COL_LAST + _COL_SILENCE + _COL_THRESH + 3)


def _row(v: WatchdogViolation) -> str:
    last = v.last_seen.isoformat(timespec="seconds") if v.last_seen else "never"
    silence = f"{v.silence_seconds:.1f}" if v.last_seen else "n/a"
    return (
        f"{v.job_name:<{_COL_JOB}} "
        f"{last:<{_COL_LAST}} "
        f"{silence:>{_COL_SILENCE}} "
        f"{v.threshold_seconds:>{_COL_THRESH}.0f}"
    )


def format_watchdog_table(violations: List[WatchdogViolation]) -> str:
    """Return a formatted table of watchdog violations, or a 'no issues' message."""
    if not violations:
        return "No watchdog violations detected."
    lines = [_header(), _sep()]
    for v in sorted(violations, key=lambda x: x.job_name):
        lines.append(_row(v))
    return "\n".join(lines)
