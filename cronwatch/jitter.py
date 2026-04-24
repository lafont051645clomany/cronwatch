"""Jitter detection: flag runs whose start times deviate significantly from their expected schedule."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from cronwatch.scheduler import next_run
from cronwatch.tracker import JobRun


@dataclass
class JitterResult:
    job_name: str
    run_id: str
    expected_at: datetime
    actual_at: datetime
    jitter_seconds: float
    exceeded_threshold: bool


def _expected_start(run: JobRun, cron_expr: str) -> Optional[datetime]:
    """Return the scheduled tick immediately before or at the run's start time."""
    if run.started_at is None:
        return None
    # Walk back one tick by finding next_run from slightly before the run
    # next_run(expr, now) returns the *next* fire after `now`, so we use
    # started_at minus one full period approximation via two consecutive calls.
    try:
        anchor = next_run(cron_expr, run.started_at)
        # anchor is the tick *after* started_at; go back one interval
        prev = next_run(cron_expr, anchor)
        interval = (prev - anchor).total_seconds()
        expected = datetime.fromtimestamp(
            anchor.timestamp() - interval, tz=timezone.utc
        )
        return expected
    except Exception:
        return None


def analyse_jitter(
    runs: List[JobRun],
    cron_expr: str,
    threshold_seconds: float = 60.0,
) -> List[JitterResult]:
    """Analyse a list of runs for start-time jitter against *cron_expr*.

    Args:
        runs: Completed or active job runs to inspect.
        cron_expr: The cron expression the job is scheduled with.
        threshold_seconds: Jitter beyond this value is flagged.

    Returns:
        A list of :class:`JitterResult` for every run that has a start time.
    """
    results: List[JitterResult] = []
    for run in runs:
        if run.started_at is None:
            continue
        expected = _expected_start(run, cron_expr)
        if expected is None:
            continue
        jitter = abs((run.started_at - expected).total_seconds())
        results.append(
            JitterResult(
                job_name=run.job_name,
                run_id=run.run_id,
                expected_at=expected,
                actual_at=run.started_at,
                jitter_seconds=jitter,
                exceeded_threshold=jitter > threshold_seconds,
            )
        )
    return results


def flagged(results: List[JitterResult]) -> List[JitterResult]:
    """Return only results that exceeded the jitter threshold."""
    return [r for r in results if r.exceeded_threshold]
