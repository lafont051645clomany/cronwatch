"""Formatting helpers for stagger violation reports."""
from __future__ import annotations

from typing import Dict, List, Tuple

from cronwatch.stagger import StaggerViolation, group_violations_by_pair

_HDR = f"{'Job A':<20} {'Job B':<20} {'Occurrences':>12} {'Min Gap (s)':>12} {'Max Gap (s)':>12}"
_SEP = "-" * len(_HDR)


def _row(
    job_a: str,
    job_b: str,
    violations: List[StaggerViolation],
) -> str:
    gaps = [v.overlap_seconds for v in violations]
    return (
        f"{job_a:<20} {job_b:<20} {len(violations):>12} "
        f"{min(gaps):>12.1f} {max(gaps):>12.1f}"
    )


def format_stagger_table(violations: List[StaggerViolation]) -> str:
    """Return a formatted table of stagger violations grouped by job pair."""
    if not violations:
        return "No stagger violations detected."

    groups = group_violations_by_pair(violations)
    lines = [_HDR, _SEP]
    for (job_a, job_b), vs in sorted(groups.items()):
        lines.append(_row(job_a, job_b, vs))
    lines.append(_SEP)
    lines.append(f"Total violations: {len(violations)}")
    return "\n".join(lines)
