"""Format escalation state for CLI display."""
from __future__ import annotations
from typing import List
from cronwatch.escalation import EscalationState

_COL = (20, 8, 22, 22)
_HDR = ("Job", "Fails", "Escalated At", "Resolved At")


def _fmt(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "-"


def _header() -> str:
    return "  ".join(h.ljust(_COL[i]) for i, h in enumerate(_HDR))


def _sep() -> str:
    return "  ".join("-" * w for w in _COL)


def _row(s: EscalationState) -> str:
    status = str(s.consecutive_failures)
    return "  ".join([
        s.job_name.ljust(_COL[0]),
        status.ljust(_COL[1]),
        _fmt(s.escalated_at).ljust(_COL[2]),
        _fmt(s.resolved_at).ljust(_COL[3]),
    ])


def format_escalation_table(states: List[EscalationState]) -> str:
    if not states:
        return "No escalated jobs."
    lines = [_header(), _sep()] + [_row(s) for s in states]
    return "\n".join(lines)
