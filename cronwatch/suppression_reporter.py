"""Format suppression-rule information as plain-text tables."""
from __future__ import annotations

from typing import List

from cronwatch.suppression import SuppressionRule

_COL = (24, 18, 14, 10, 30)


def _header() -> str:
    h = (
        f"{'Rule':<{_COL[0]}}"
        f"{'Jobs':<{_COL[1]}}"
        f"{'Statuses':<{_COL[2]}}"
        f"{'MaxDur(s)':<{_COL[3]}}"
        f"{'Reason':<{_COL[4]}}"
    )
    return h


def _sep() -> str:
    return "-" * sum(_COL)


def _row(rule: SuppressionRule) -> str:
    jobs = ",".join(rule.job_names) if rule.job_names else "*"
    statuses = ",".join(s.value for s in rule.statuses) if rule.statuses else "*"
    max_dur = str(rule.max_duration) if rule.max_duration is not None else "*"
    reason = rule.reason or ""
    return (
        f"{rule.name:<{_COL[0]}}"
        f"{jobs:<{_COL[1]}}"
        f"{statuses:<{_COL[2]}}"
        f"{max_dur:<{_COL[3]}}"
        f"{reason:<{_COL[4]}}"
    )


def format_suppression_table(rules: List[SuppressionRule]) -> str:
    """Return a formatted table of suppression rules."""
    if not rules:
        return "No suppression rules configured."
    lines = [_header(), _sep()]
    for rule in rules:
        lines.append(_row(rule))
    return "\n".join(lines)
