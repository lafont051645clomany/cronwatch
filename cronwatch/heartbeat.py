"""Heartbeat tracking — detect jobs that have stopped reporting entirely."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from cronwatch.tracker import JobRun


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class HeartbeatConfig:
    """Per-job heartbeat expectation."""
    job_name: str
    max_silence: timedelta  # alert if no run seen within this period


@dataclass
class HeartbeatViolation:
    job_name: str
    last_seen: Optional[datetime]  # None if the job has never run
    silence_duration: Optional[timedelta]
    threshold: timedelta

    def message(self) -> str:
        if self.last_seen is None:
            return (
                f"Job '{self.job_name}' has never reported a heartbeat "
                f"(threshold: {self.threshold})."
            )
        secs = int(self.silence_duration.total_seconds())
        limit = int(self.threshold.total_seconds())
        return (
            f"Job '{self.job_name}' silent for {secs}s "
            f"(threshold: {limit}s, last seen: {self.last_seen.isoformat()})."
        )


class HeartbeatMonitor:
    """Tracks the most recent run per job and checks for silence violations."""

    def __init__(self, configs: List[HeartbeatConfig]) -> None:
        self._configs: Dict[str, HeartbeatConfig] = {
            c.job_name: c for c in configs
        }
        self._last_seen: Dict[str, datetime] = {}

    def record(self, run: JobRun) -> None:
        """Update the last-seen timestamp for a job from a completed run."""
        ts = run.finished_at or run.started_at
        if ts is None:
            return
        prev = self._last_seen.get(run.job_name)
        if prev is None or ts > prev:
            self._last_seen[run.job_name] = ts

    def check(self, at: Optional[datetime] = None) -> List[HeartbeatViolation]:
        """Return violations for every configured job that has gone silent."""
        now = at or _now()
        violations: List[HeartbeatViolation] = []
        for job_name, cfg in self._configs.items():
            last = self._last_seen.get(job_name)
            if last is None:
                violations.append(
                    HeartbeatViolation(
                        job_name=job_name,
                        last_seen=None,
                        silence_duration=None,
                        threshold=cfg.max_silence,
                    )
                )
            else:
                silence = now - last
                if silence > cfg.max_silence:
                    violations.append(
                        HeartbeatViolation(
                            job_name=job_name,
                            last_seen=last,
                            silence_duration=silence,
                            threshold=cfg.max_silence,
                        )
                    )
        return violations
