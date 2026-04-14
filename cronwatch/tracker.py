"""Job execution tracker: records start/end times and detects delays or failures."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from cronwatch.config import JobConfig


class JobStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class JobRun:
    job_name: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    status: JobStatus = JobStatus.RUNNING
    exit_code: Optional[int] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    def finish(self, exit_code: int) -> None:
        self.finished_at = datetime.utcnow()
        self.exit_code = exit_code
        self.status = JobStatus.SUCCESS if exit_code == 0 else JobStatus.FAILED


class JobTracker:
    """Tracks in-progress and completed job runs."""

    def __init__(self) -> None:
        self._active: Dict[str, JobRun] = {}
        self._history: list[JobRun] = []

    def start(self, job_name: str) -> JobRun:
        run = JobRun(job_name=job_name)
        self._active[job_name] = run
        return run

    def finish(self, job_name: str, exit_code: int) -> Optional[JobRun]:
        run = self._active.pop(job_name, None)
        if run is None:
            return None
        run.finish(exit_code)
        self._history.append(run)
        return run

    def check_timeouts(self, jobs: Dict[str, JobConfig]) -> list[JobRun]:
        """Return active runs that have exceeded their configured max_duration."""
        timed_out = []
        now = datetime.utcnow()
        for job_name, run in list(self._active.items()):
            cfg = jobs.get(job_name)
            if cfg and cfg.max_duration is not None:
                elapsed = (now - run.started_at).total_seconds()
                if elapsed > cfg.max_duration:
                    run.status = JobStatus.TIMEOUT
                    timed_out.append(run)
        return timed_out

    @property
    def history(self) -> list[JobRun]:
        return list(self._history)

    @property
    def active(self) -> Dict[str, JobRun]:
        return dict(self._active)
