"""Correlate job runs across jobs to detect cascading failures."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List

from cronwatch.tracker import JobRun, JobStatus


@dataclass
class CorrelationWindow:
    job_name: str
    failures: List[datetime] = field(default_factory=list)


@dataclass
class CorrelationResult:
    anchor_job: str
    related_job: str
    overlap_count: int
    window_seconds: float


def _failure_times(runs: List[JobRun]) -> List[datetime]:
    return [
        r.finished_at
        for r in runs
        if r.status == JobStatus.FAILURE and r.finished_at is not None
    ]


def correlate(
    anchor_runs: List[JobRun],
    candidate_runs: Dict[str, List[JobRun]],
    window: timedelta = timedelta(minutes=5),
) -> List[CorrelationResult]:
    """Return jobs whose failures cluster within *window* of anchor failures."""
    anchor_failures = _failure_times(anchor_runs)
    if not anchor_failures:
        return []

    anchor_name = anchor_runs[0].job_name
    results: List[CorrelationResult] = []

    for job_name, runs in candidate_runs.items():
        if job_name == anchor_name:
            continue
        candidate_failures = _failure_times(runs)
        overlap = 0
        for af in anchor_failures:
            for cf in candidate_failures:
                if abs((cf - af).total_seconds()) <= window.total_seconds():
                    overlap += 1
                    break
        if overlap:
            results.append(
                CorrelationResult(
                    anchor_job=anchor_name,
                    related_job=job_name,
                    overlap_count=overlap,
                    window_seconds=window.total_seconds(),
                )
            )

    results.sort(key=lambda r: r.overlap_count, reverse=True)
    return results
