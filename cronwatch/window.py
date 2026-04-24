"""Sliding window statistics for cron job run durations and failure rates."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from cronwatch.tracker import JobRun, JobStatus


@dataclass
class WindowConfig:
    size_minutes: int = 60
    min_samples: int = 3


@dataclass
class WindowStats:
    job_name: str
    window_minutes: int
    sample_count: int
    failure_count: int
    avg_duration: Optional[float]  # seconds
    p95_duration: Optional[float]  # seconds
    failure_rate: float

    @property
    def has_enough_samples(self) -> bool:
        return self.sample_count > 0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _durations(runs: List[JobRun]) -> List[float]:
    return [
        r.duration_seconds
        for r in runs
        if r.duration_seconds is not None
    ]


def _percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * pct / 100)
    idx = min(idx, len(sorted_vals) - 1)
    return sorted_vals[idx]


def compute_window_stats(
    job_name: str,
    runs: List[JobRun],
    cfg: WindowConfig,
    now: Optional[datetime] = None,
) -> WindowStats:
    """Compute sliding-window statistics for a single job."""
    if now is None:
        now = _now()
    cutoff = now - timedelta(minutes=cfg.size_minutes)

    window_runs = [
        r for r in runs
        if r.job_name == job_name
        and r.started_at is not None
        and r.started_at >= cutoff
    ]

    failures = [r for r in window_runs if r.status == JobStatus.FAILED]
    durations = _durations(window_runs)
    avg = sum(durations) / len(durations) if durations else None
    p95 = _percentile(durations, 95)
    rate = len(failures) / len(window_runs) if window_runs else 0.0

    return WindowStats(
        job_name=job_name,
        window_minutes=cfg.size_minutes,
        sample_count=len(window_runs),
        failure_count=len(failures),
        avg_duration=avg,
        p95_duration=p95,
        failure_rate=rate,
    )


def compute_all(
    runs: List[JobRun],
    cfg: WindowConfig,
    now: Optional[datetime] = None,
) -> List[WindowStats]:
    """Compute window stats for every distinct job in *runs*."""
    names = sorted({r.job_name for r in runs})
    return [compute_window_stats(name, runs, cfg, now) for name in names]
