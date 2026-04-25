"""Retention policy: automatically expire and remove old job run history."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from cronwatch.tracker import JobRun, JobStatus


@dataclass
class RetentionConfig:
    """Policy controlling how long run history is kept."""
    max_age_days: Optional[int] = 90          # drop runs older than this
    max_runs_per_job: Optional[int] = 500     # keep at most N runs per job
    keep_failures: bool = True                # never drop failed/timeout runs


@dataclass
class RetentionResult:
    total_before: int
    total_after: int
    dropped: int
    kept_due_to_failure: int

    @property
    def summary(self) -> str:
        return (
            f"Retention: {self.total_before} → {self.total_after} runs "
            f"({self.dropped} dropped, {self.kept_due_to_failure} failure-protected)"
        )


def _is_failure(run: JobRun) -> bool:
    return run.status in (JobStatus.FAILED, JobStatus.TIMEOUT)


def apply_retention(
    runs: List[JobRun],
    config: RetentionConfig,
    now: Optional[datetime] = None,
) -> tuple[List[JobRun], RetentionResult]:
    """Return a filtered list of runs that satisfy *config*.

    Runs are processed per-job so that ``max_runs_per_job`` applies
    independently to each job name.
    """
    if now is None:
        now = datetime.now(tz=timezone.utc)

    cutoff = (
        now - timedelta(days=config.max_age_days)
        if config.max_age_days is not None
        else None
    )

    kept_due_to_failure = 0
    kept: List[JobRun] = []
    dropped = 0

    # Group by job name, preserving insertion order
    jobs: dict[str, List[JobRun]] = {}
    for run in runs:
        jobs.setdefault(run.job_name, []).append(run)

    for job_runs in jobs.values():
        # Sort newest-first so count-based trimming keeps the most recent
        job_runs.sort(key=lambda r: r.started_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

        surviving: List[JobRun] = []
        for idx, run in enumerate(job_runs):
            age_ok = cutoff is None or (run.started_at is not None and run.started_at >= cutoff)
            count_ok = config.max_runs_per_job is None or idx < config.max_runs_per_job
            is_fail = _is_failure(run)

            if age_ok and count_ok:
                surviving.append(run)
            elif config.keep_failures and is_fail:
                surviving.append(run)
                kept_due_to_failure += 1
            else:
                dropped += 1

        kept.extend(surviving)

    result = RetentionResult(
        total_before=len(runs),
        total_after=len(kept),
        dropped=dropped,
        kept_due_to_failure=kept_due_to_failure,
    )
    return kept, result
