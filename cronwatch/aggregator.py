"""Aggregate JobRun lists into per-job bucketed time series data."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Literal, Sequence

from cronwatch.tracker import JobRun, JobStatus

Period = Literal["minute", "hour", "day"]


def _bucket_key(dt: datetime, period: Period) -> datetime:
    """Truncate *dt* to the start of the given *period*."""
    if period == "minute":
        return dt.replace(second=0, microsecond=0)
    if period == "hour":
        return dt.replace(minute=0, second=0, microsecond=0)
    # day
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


@dataclass
class Bucket:
    period_start: datetime
    total: int = 0
    failures: int = 0
    durations: List[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.total - self.failures) / self.total

    @property
    def avg_duration(self) -> float | None:
        return sum(self.durations) / len(self.durations) if self.durations else None


def aggregate(
    runs: Sequence[JobRun],
    period: Period = "hour",
    job_name: str | None = None,
) -> Dict[str, List[Bucket]]:
    """Return a dict mapping job name -> list of :class:`Bucket` sorted by time.

    Parameters
    ----------
    runs:
        All job runs to consider.
    period:
        Granularity of each bucket (``"minute"``, ``"hour"``, or ``"day"``).
    job_name:
        When provided, only aggregate runs for that job.
    """
    filtered = [
        r for r in runs
        if r.started_at is not None and (job_name is None or r.job_name == job_name)
    ]

    # job -> bucket_key -> Bucket
    buckets: Dict[str, Dict[datetime, Bucket]] = defaultdict(dict)

    for run in filtered:
        key = _bucket_key(run.started_at, period)  # type: ignore[arg-type]
        job_buckets = buckets[run.job_name]
        if key not in job_buckets:
            job_buckets[key] = Bucket(period_start=key)
        bucket = job_buckets[key]
        bucket.total += 1
        if run.status == JobStatus.FAILED:
            bucket.failures += 1
        dur = run.duration_seconds()
        if dur is not None:
            bucket.durations.append(dur)

    return {
        job: sorted(bkts.values(), key=lambda b: b.period_start)
        for job, bkts in buckets.items()
    }
