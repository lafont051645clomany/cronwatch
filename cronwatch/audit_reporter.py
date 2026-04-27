"""Format AuditEntry lists as human-readable tables."""
from __future__ import annotations

from typing import List

from cronwatch.audit import AuditEntry

_DT_FMT = "%Y-%m-%d %H:%M:%S"


def _fmt_dt(entry: AuditEntry) -> str:
    return entry.timestamp.strftime(_DT_FMT)


_HEADER = ("Timestamp", "Job", "Event", "Status", "Channel", "Detail")
_WIDTHS = (19, 20, 22, 10, 12, 30)


def _sep() -> str:
    return "+" + "+".join("-" * (w + 2) for w in _WIDTHS) + "+"


def _row(*cells: str) -> str:
    parts = []
    for cell, w in zip(cells, _WIDTHS):
        parts.append(f" {str(cell):<{w}} ")
    return "|" + "|".join(parts) + "|"


def format_audit_table(entries: List[AuditEntry]) -> str:
    """Return a formatted table string for *entries*."""
    if not entries:
        return "No audit entries found."

    lines = [
        _sep(),
        _row(*_HEADER),
        _sep(),
    ]
    for e in entries:
        detail = (e.detail or "")[:28]
        lines.append(
            _row(
                _fmt_dt(e),
                e.job_name[:18],
                e.event[:20],
                e.status[:8],
                (e.channel or "")[:10],
                detail,
            )
        )
    lines.append(_sep())
    return "\n".join(lines)


def format_audit_summary(entries: List[AuditEntry]) -> str:
    """Return a one-line summary: totals by status."""
    if not entries:
        return "Audit log is empty."
    counts: dict[str, int] = {}
    for e in entries:
        counts[e.status] = counts.get(e.status, 0) + 1
    parts = ", ".join(f"{s}: {c}" for s, c in sorted(counts.items()))
    return f"Audit entries: {len(entries)} total — {parts}"
