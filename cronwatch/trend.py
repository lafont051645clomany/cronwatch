"""Trend analysis: detect improving/degrading job performance over time."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from cronwatch.tracker import JobRun, JobStatus


@dataclass
class TrendResult:
    job_name: str
    sample_count: int
    direction: str  # 'improving', 'degrading', 'stable', 'insufficient'
    slope: Optional[float]  # seconds per run, positive = slower over time
    failure_rate_delta: Optional[float]  # positive = more failures recently


def _linear_slope(values: List[float]) -> float:
    """Least-squares slope for evenly-spaced samples."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den else 0.0


def analyse_trend(
    runs: List[JobRun],
    job_name: str,
    min_samples: int = 5,
    slope_threshold: float = 1.0,
) -> TrendResult:
    """Analyse duration trend for a single job's runs."""
    job_runs = [r for r in runs if r.job_name == job_name]
    job_runs.sort(key=lambda r: r.started_at)

    if len(job_runs) < min_samples:
        return TrendResult(job_name, len(job_runs), 'insufficient', None, None)

    durations = [
        r.duration_seconds() for r in job_runs if r.duration_seconds() is not None
    ]
    slope = _linear_slope(durations) if len(durations) >= min_samples else 0.0

    half = len(job_runs) // 2
    def _fail_rate(subset):
        return sum(1 for r in subset if r.status == JobStatus.FAILURE) / len(subset)

    delta = _fail_rate(job_runs[half:]) - _fail_rate(job_runs[:half])

    if slope > slope_threshold or delta > 0.1:
        direction = 'degrading'
    elif slope < -slope_threshold or delta < -0.1:
        direction = 'improving'
    else:
        direction = 'stable'

    return TrendResult(job_name, len(job_runs), direction, slope, delta)
