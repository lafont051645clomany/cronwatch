"""Formatting helpers for SLA violation reports."""
from __future__ import annotations

from typing import List

from cronwatch.sla import SLAViolation

_COL_JOB = 24
_COL_REASON = 56


def _header() -> str:
    return (
        f"{'Job':<{_COL_JOB}}  {'Reason':<{_COL_REASON}}  Measured At"
    )


def _sep() -> str:
    return "-" * (_COL_JOB + 2 + _COL_REASON + 2 + 20)


def _row(v: SLAViolation) -> str:
    ts = v.measured_at.strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"{v.job_name:<{_COL_JOB}}  "
        f"{v.reason:<{_COL_REASON}}  "
        f"{ts}"
    )


def format_sla_table(violations: List[SLAViolation]) -> str:
    """Render a plain-text table of SLA violations.

    Returns a short message when there are no violations.
    """
    if not violations:
        return "No SLA violations detected."

    lines = [_header(), _sep()]
    for v in violations:
        lines.append(_row(v))
    lines.append(_sep())
    lines.append(f"{len(violations)} violation(s) found.")
    return "\n".join(lines)
