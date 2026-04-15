"""Filter utilities for selecting JobRun records by various criteria."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Iterable, List, Optional

from cronwatch.tracker import JobRun, JobStatus


def by_job_name(runs: Iterable[JobRun], name: str) -> List[JobRun]:
    """Return only runs whose job_name matches *name* (case-insensitive)."""
    name_lower = name.lower()
    return [r for r in runs if r.job_name.lower() == name_lower]


def by_status(runs: Iterable[JobRun], status: JobStatus) -> List[JobRun]:
    """Return only runs with the given *status*."""
    return [r for r in runs if r.status == status]


def by_time_range(
    runs: Iterable[JobRun],
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> List[JobRun]:
    """Return runs whose *started_at* falls within [since, until].

    Either bound may be *None* to indicate an open interval.
    """
    result: List[JobRun] = []
    for run in runs:
        if since is not None and run.started_at < since:
            continue
        if until is not None and run.started_at > until:
            continue
        result.append(run)
    return result


def by_predicate(runs: Iterable[JobRun], predicate: Callable[[JobRun], bool]) -> List[JobRun]:
    """Return runs that satisfy an arbitrary *predicate* callable."""
    return [r for r in runs if predicate(r)]


def apply_filters(
    runs: Iterable[JobRun],
    *,
    job_name: Optional[str] = None,
    status: Optional[JobStatus] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> List[JobRun]:
    """Convenience wrapper that chains multiple filters in one call.

    Filters are applied in order; any *None* argument is skipped.
    """
    result: List[JobRun] = list(runs)
    if job_name is not None:
        result = by_job_name(result, job_name)
    if status is not None:
        result = by_status(result, status)
    if since is not None or until is not None:
        result = by_time_range(result, since=since, until=until)
    return result
