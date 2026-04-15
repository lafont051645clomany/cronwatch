"""Lightweight in-process metrics collection for cron job runs."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatch.tracker import JobRun, JobStatus


@dataclass
class JobMetrics:
    """Aggregated metrics for a single job."""

    job_name: str
    total_runs: int = 0
    success_count: int = 0
    failure_count: int = 0
    timeout_count: int = 0
    durations: List[float] = field(default_factory=list)

    @property
    def success_rate(self) -> Optional[float]:
        if self.total_runs == 0:
            return None
        return self.success_count / self.total_runs

    @property
    def avg_duration(self) -> Optional[float]:
        if not self.durations:
            return None
        return sum(self.durations) / len(self.durations)

    @property
    def max_duration(self) -> Optional[float]:
        return max(self.durations) if self.durations else None

    @property
    def min_duration(self) -> Optional[float]:
        return min(self.durations) if self.durations else None


def compute_metrics(runs: List[JobRun]) -> Dict[str, JobMetrics]:
    """Compute per-job metrics from a list of JobRun objects."""
    metrics: Dict[str, JobMetrics] = defaultdict(lambda: JobMetrics(job_name=""))

    for run in runs:
        m = metrics[run.job_name]
        m.job_name = run.job_name
        m.total_runs += 1

        if run.status == JobStatus.SUCCESS:
            m.success_count += 1
        elif run.status == JobStatus.FAILURE:
            m.failure_count += 1
        elif run.status == JobStatus.TIMEOUT:
            m.timeout_count += 1

        dur = run.duration_seconds()
        if dur is not None:
            m.durations.append(dur)

    return dict(metrics)


def top_failing_jobs(metrics: Dict[str, JobMetrics], n: int = 5) -> List[JobMetrics]:
    """Return the top-n jobs by failure count, descending."""
    ranked = sorted(metrics.values(), key=lambda m: m.failure_count, reverse=True)
    return ranked[:n]
