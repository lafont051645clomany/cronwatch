"""Job run quota enforcement — limit how many times a job may run in a period."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List


@dataclass
class QuotaConfig:
    max_runs: int
    period_seconds: int  # rolling window


@dataclass
class _Window:
    timestamps: List[datetime] = field(default_factory=list)


class QuotaTracker:
    """Track run counts per job within a rolling time window."""

    def __init__(self) -> None:
        self._windows: Dict[str, _Window] = {}

    def _evict(self, job: str, now: datetime, period: timedelta) -> None:
        win = self._windows.get(job)
        if win is None:
            return
        cutoff = now - period
        win.timestamps = [t for t in win.timestamps if t > cutoff]

    def record(self, job: str, at: datetime | None = None) -> None:
        """Record a run occurrence for *job*."""
        now = at or datetime.utcnow()
        win = self._windows.setdefault(job, _Window())
        win.timestamps.append(now)

    def count(self, job: str, cfg: QuotaConfig, now: datetime | None = None) -> int:
        """Return number of runs for *job* within the quota window."""
        now = now or datetime.utcnow()
        self._evict(job, now, timedelta(seconds=cfg.period_seconds))
        win = self._windows.get(job)
        return len(win.timestamps) if win else 0

    def is_exceeded(self, job: str, cfg: QuotaConfig, now: datetime | None = None) -> bool:
        """Return True if the job has exceeded its allowed run quota."""
        return self.count(job, cfg, now) > cfg.max_runs

    def remaining(self, job: str, cfg: QuotaConfig, now: datetime | None = None) -> int:
        """Return how many more runs are permitted in the current window."""
        return max(0, cfg.max_runs - self.count(job, cfg, now))
