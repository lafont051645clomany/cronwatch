"""Formatting helpers for RunLog entries."""
from __future__ import annotations

from typing import List, Optional

from cronwatch.runlog import RunLogEntry

_COL_JOB = 20
_COL_STATUS = 10
_COL_STARTED = 22
_COL_DUR = 10
_COL_EXIT = 6
_COL_NOTE = 24


def _fmt_dt(dt) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _fmt_dur(v: Optional[float]) -> str:
    if v is None:
        return "—"
    if v < 60:
        return f"{v:.1f}s"
    return f"{v / 60:.1f}m"


def _header() -> str:
    return (
        f"{'Job':<{_COL_JOB}} "
        f"{'Status':<{_COL_STATUS}} "
        f"{'Started':<{_COL_STARTED}} "
        f"{'Duration':<{_COL_DUR}} "
        f"{'Exit':<{_COL_EXIT}} "
        f"{'Note':<{_COL_NOTE}}"
    )


def _sep() -> str:
    return "-" * (
        _COL_JOB + _COL_STATUS + _COL_STARTED + _COL_DUR + _COL_EXIT + _COL_NOTE + 5
    )


def _row(e: RunLogEntry) -> str:
    return (
        f"{e.job_name:<{_COL_JOB}} "
        f"{e.status:<{_COL_STATUS}} "
        f"{_fmt_dt(e.started_at):<{_COL_STARTED}} "
        f"{_fmt_dur(e.duration_seconds):<{_COL_DUR}} "
        f"{str(e.exit_code or ''):<{_COL_EXIT}} "
        f"{e.note:<{_COL_NOTE}}"
    )


def format_runlog_table(entries: List[RunLogEntry]) -> str:
    if not entries:
        return "No run log entries found."
    lines = [_header(), _sep()]
    for e in entries:
        lines.append(_row(e))
    return "\n".join(lines)


def format_runlog_summary(entries: List[RunLogEntry]) -> str:
    if not entries:
        return "No entries."
    total = len(entries)
    failed = sum(1 for e in entries if e.status in ("failure", "timeout"))
    success = sum(1 for e in entries if e.status == "success")
    durations = [e.duration_seconds for e in entries if e.duration_seconds is not None]
    avg = sum(durations) / len(durations) if durations else None
    lines = [
        f"Total runs : {total}",
        f"Successes  : {success}",
        f"Failures   : {failed}",
        f"Avg dur    : {_fmt_dur(avg)}",
    ]
    return "\n".join(lines)
