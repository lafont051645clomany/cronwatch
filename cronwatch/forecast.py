"""Forecast future job failure probability based on historical trend."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from cronwatch.tracker import JobRun
from cronwatch.trend import _linear_slope, _fail_rate

_MIN_SAMPLES = 5


@dataclass
class ForecastResult:
    job_name: str
    samples: int
    current_fail_rate: float          # 0.0 – 1.0
    slope_per_hour: Optional[float]   # change in fail-rate per hour; None if insufficient
    predicted_fail_rate_1h: Optional[float]
    predicted_fail_rate_24h: Optional[float]
    confidence: str                   # "low" | "medium" | "high"

    @property
    def is_degrading(self) -> bool:
        return self.slope_per_hour is not None and self.slope_per_hour > 0


def _bucket_fail_rates(runs: List[JobRun], bucket_minutes: int = 60) -> List[float]:
    """Group runs into time buckets and return per-bucket failure rates."""
    if not runs:
        return []
    sorted_runs = sorted(runs, key=lambda r: r.started_at or datetime.min)
    buckets: dict[int, list[JobRun]] = {}
    origin = sorted_runs[0].started_at or datetime.min
    for run in sorted_runs:
        t = run.started_at or origin
        bucket = int((t - origin).total_seconds() / (bucket_minutes * 60))
        buckets.setdefault(bucket, []).append(run)
    return [_fail_rate(b) for b in buckets.values()]


def forecast(job_name: str, runs: List[JobRun]) -> ForecastResult:
    """Compute a failure-rate forecast for *job_name* from its run history."""
    job_runs = [r for r in runs if r.job_name == job_name]
    n = len(job_runs)
    current = _fail_rate(job_runs)

    if n < _MIN_SAMPLES:
        return ForecastResult(
            job_name=job_name,
            samples=n,
            current_fail_rate=current,
            slope_per_hour=None,
            predicted_fail_rate_1h=None,
            predicted_fail_rate_24h=None,
            confidence="low",
        )

    rates = _bucket_fail_rates(job_runs)
    slope = _linear_slope(rates)  # change per bucket (1 h)

    def _clamp(v: float) -> float:
        return max(0.0, min(1.0, v))

    pred_1h = _clamp(current + slope) if slope is not None else None
    pred_24h = _clamp(current + slope * 24) if slope is not None else None
    confidence = "high" if n >= 20 else "medium"

    return ForecastResult(
        job_name=job_name,
        samples=n,
        current_fail_rate=current,
        slope_per_hour=slope,
        predicted_fail_rate_1h=pred_1h,
        predicted_fail_rate_24h=pred_24h,
        confidence=confidence,
    )
