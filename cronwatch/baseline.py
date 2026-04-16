"""Baseline duration tracking for cron jobs.

Captures the expected (baseline) duration for each job based on historical
runs and exposes helpers to detect anomalous run times.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatch.tracker import JobRun, JobStatus


@dataclass
class BaselineStats:
    job_name: str
    sample_count: int = 0
    mean_seconds: float = 0.0
    stddev_seconds: float = 0.0

    def is_anomalous(self, duration: float, threshold_sigma: float = 2.0) -> bool:
        """Return True if *duration* deviates beyond *threshold_sigma* standard
        deviations from the recorded mean."""
        if self.sample_count < 2 or self.stddev_seconds == 0.0:
            return False
        z = abs(duration - self.mean_seconds) / self.stddev_seconds
        return z > threshold_sigma


def compute_baseline(job_name: str, runs: List[JobRun]) -> BaselineStats:
    """Compute baseline statistics from a list of successful *runs*."""
    durations = [
        r.duration_seconds()
        for r in runs
        if r.job_name == job_name
        and r.status == JobStatus.SUCCESS
        and r.duration_seconds() is not None
    ]
    n = len(durations)
    if n == 0:
        return BaselineStats(job_name=job_name)
    mean = sum(durations) / n
    variance = sum((d - mean) ** 2 for d in durations) / n
    stddev = variance ** 0.5
    return BaselineStats(
        job_name=job_name,
        sample_count=n,
        mean_seconds=round(mean, 3),
        stddev_seconds=round(stddev, 3),
    )


class BaselineStore:
    """Persist and retrieve baseline stats as JSON."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._data: Dict[str, BaselineStats] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        with open(self._path, "r") as fh:
            raw = json.load(fh)
        for job_name, rec in raw.items():
            self._data[job_name] = BaselineStats(
                job_name=job_name,
                sample_count=rec["sample_count"],
                mean_seconds=rec["mean_seconds"],
                stddev_seconds=rec["stddev_seconds"],
            )

    def save(self) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        raw = {
            name: {
                "sample_count": s.sample_count,
                "mean_seconds": s.mean_seconds,
                "stddev_seconds": s.stddev_seconds,
            }
            for name, s in self._data.items()
        }
        with open(self._path, "w") as fh:
            json.dump(raw, fh, indent=2)

    def update(self, stats: BaselineStats) -> None:
        self._data[stats.job_name] = stats

    def get(self, job_name: str) -> Optional[BaselineStats]:
        return self._data.get(job_name)

    def all(self) -> Dict[str, BaselineStats]:
        return dict(self._data)
