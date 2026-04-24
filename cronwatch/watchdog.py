"""Watchdog: detect jobs that have not been seen within an expected interval."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from cronwatch.tracker import JobRun


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class WatchdogConfig:
    """Per-job watchdog settings."""
    job_name: str
    max_silence_seconds: float  # alert if no run seen within this window
    enabled: bool = True


@dataclass
class WatchdogViolation:
    """Emitted when a job has been silent too long."""
    job_name: str
    last_seen: Optional[datetime]  # None if never run
    silence_seconds: float
    threshold_seconds: float

    @property
    def message(self) -> str:
        if self.last_seen is None:
            return (
                f"Job '{self.job_name}' has never been seen "
                f"(threshold {self.threshold_seconds:.0f}s)."
            )
        return (
            f"Job '{self.job_name}' silent for {self.silence_seconds:.1f}s "
            f"(threshold {self.threshold_seconds:.0f}s, "
            f"last seen {self.last_seen.isoformat()})."
        )


class Watchdog:
    """Check whether monitored jobs have produced a run recently enough."""

    def __init__(self, configs: List[WatchdogConfig]) -> None:
        self._configs: Dict[str, WatchdogConfig] = {
            c.job_name: c for c in configs
        }

    def check(self, runs: List[JobRun]) -> List[WatchdogViolation]:
        """Return violations for any job whose last run exceeds its threshold."""
        last_seen: Dict[str, datetime] = {}
        for run in runs:
            ts = run.finished_at or run.started_at
            if ts is None:
                continue
            if run.job_name not in last_seen or ts > last_seen[run.job_name]:
                last_seen[run.job_name] = ts

        now = _now()
        violations: List[WatchdogViolation] = []
        for job_name, cfg in self._configs.items():
            if not cfg.enabled:
                continue
            seen_at = last_seen.get(job_name)
            if seen_at is None:
                silence = cfg.max_silence_seconds + 1  # treat as exceeded
            else:
                silence = (now - seen_at).total_seconds()

            if silence > cfg.max_silence_seconds:
                violations.append(
                    WatchdogViolation(
                        job_name=job_name,
                        last_seen=seen_at,
                        silence_seconds=silence,
                        threshold_seconds=cfg.max_silence_seconds,
                    )
                )
        return violations
