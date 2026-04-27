"""Format incident data as plain-text tables for CLI output."""
from __future__ import annotations

from typing import List

from cronwatch.incident import Incident

_COL = (20, 24, 8, 10, 24)


def _header() -> str:
    return (
        f"{'Job':<{_COL[0]}}  {'Started':<{_COL[1]}}  "
        f"{'Failures':>{_COL[2]}}  {'Status':<{_COL[3]}}  "
        f"{'Resolved':<{_COL[4]}}"
    )


def _sep() -> str:
    return "  ".join("-" * w for w in _COL)


def _row(inc: Incident) -> str:
    started = inc.started_at.strftime("%Y-%m-%d %H:%M:%S")
    status = "OPEN" if inc.is_open else "RESOLVED"
    resolved = (
        inc.resolved_at.strftime("%Y-%m-%d %H:%M:%S")
        if inc.resolved_at
        else "—"
    )
    return (
        f"{inc.job_name:<{_COL[0]}}  {started:<{_COL[1]}}  "
        f"{inc.failure_count:>{_COL[2]}}  {status:<{_COL[3]}}  "
        f"{resolved:<{_COL[4]}}"
    )


def format_incident_table(incidents: List[Incident]) -> str:
    if not incidents:
        return "No incidents recorded."
    lines = [_header(), _sep()]
    for inc in incidents:
        lines.append(_row(inc))
    return "\n".join(lines)


def format_incident_summary(incidents: List[Incident]) -> str:
    total = len(incidents)
    open_count = sum(1 for i in incidents if i.is_open)
    resolved_count = total - open_count
    return (
        f"Incidents: {total} total, {open_count} open, {resolved_count} resolved."
    )
