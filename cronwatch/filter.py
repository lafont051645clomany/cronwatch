"""Composable predicates for filtering collections of :class:`JobRun` objects."""
from __future__ import annotations

from datetime import datetime
from typing import Callable, Iterable, List, Optional

from cronwatch.tracker import JobRun, JobStatus


def by_job_name(name: str) -> Callable[[JobRun], bool]:
    """Match runs whose ``job_name`` equals *name* (case-insensitive)."""
    name_lower = name.lower()

    def _pred(run: JobRun) -> bool:
        return run.job_name.lower() == name_lower

    return _pred


def by_status(status: JobStatus) -> Callable[[JobRun], bool]:
    """Match runs with the given :class:`JobStatus`."""

    def _pred(run: JobRun) -> bool:
        return run.status == status

    return _pred


def by_time_range(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> Callable[[JobRun], bool]:
    """Match runs whose ``started_at`` falls within [*start*, *end*].

    Either bound may be *None* to leave that side open.
    """

    def _pred(run: JobRun) -> bool:
        if start is not None and run.started_at < start:
            return False
        if end is not None and run.started_at > end:
            return False
        return True

    return _pred


def by_tag(tag: str) -> Callable[[JobRun], bool]:
    """Match runs that carry *tag* (case-insensitive) in their ``tags`` list."""
    tag_lower = tag.lower()

    def _pred(run: JobRun) -> bool:
        run_tags = getattr(run, "tags", None) or []
        return any(t.lower() == tag_lower for t in run_tags)

    return _pred


def by_predicate(predicate: Callable[[JobRun], bool]) -> Callable[[JobRun], bool]:
    """Wrap an arbitrary predicate so it can be composed with the others."""
    return predicate


def apply_filters(
    runs: Iterable[JobRun],
    *predicates: Callable[[JobRun], bool],
) -> List[JobRun]:
    """Return the subset of *runs* that satisfies **all** *predicates*."""
    result = list(runs)
    for pred in predicates:
        result = [r for r in result if pred(r)]
    return result
