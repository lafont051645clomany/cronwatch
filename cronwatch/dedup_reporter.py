"""Formatting helpers for deduplication state reports."""

from __future__ import annotations

from typing import List, Tuple

from cronwatch.dedup import DedupTracker


def _header() -> str:
    return f"{'Job':<30} {'Status':<12} {'Count':>7} {'Suppressing?':>13}"


def _sep() -> str:
    return "-" * 66


def _row(job: str, status: str, count: int, suppressing: bool) -> str:
    flag = "yes" if suppressing else "no"
    return f"{job:<30} {status:<12} {count:>7} {flag:>13}"


def format_dedup_table(
    tracker: DedupTracker,
    pairs: List[Tuple[str, str]],
) -> str:
    """Render a table showing dedup state for the given (job, status) pairs."""
    if not pairs:
        return "No dedup entries tracked."

    lines = [_header(), _sep()]
    for job_name, status in sorted(pairs):
        count = tracker.get_count(job_name, status)
        suppressing = tracker.is_duplicate(job_name, status)
        lines.append(_row(job_name, status, count, suppressing))
    return "\n".join(lines)
