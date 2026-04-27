"""Incident tracking: group consecutive failures into named incidents."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from cronwatch.tracker import JobRun, JobStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Incident:
    job_name: str
    started_at: datetime
    failure_count: int = 0
    resolved_at: Optional[datetime] = None
    run_ids: List[str] = field(default_factory=list)

    @property
    def is_open(self) -> bool:
        return self.resolved_at is None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.resolved_at is None:
            return None
        return (self.resolved_at - self.started_at).total_seconds()

    def message(self) -> str:
        status = "OPEN" if self.is_open else "RESOLVED"
        return (
            f"[{status}] {self.job_name}: {self.failure_count} failure(s) "
            f"since {self.started_at.isoformat()}"
        )


class IncidentTracker:
    """Tracks open incidents per job, opening/resolving as runs arrive."""

    def __init__(self) -> None:
        self._open: Dict[str, Incident] = {}
        self._closed: List[Incident] = []

    def record(self, run: JobRun) -> Optional[Incident]:
        """Process a run. Returns the affected Incident (open or just resolved)."""
        name = run.job_name
        if run.status == JobStatus.FAILURE:
            if name not in self._open:
                self._open[name] = Incident(
                    job_name=name,
                    started_at=run.started_at or _now(),
                )
            inc = self._open[name]
            inc.failure_count += 1
            if run.run_id:
                inc.run_ids.append(run.run_id)
            return inc
        else:
            if name in self._open:
                inc = self._open.pop(name)
                inc.resolved_at = run.finished_at or _now()
                self._closed.append(inc)
                return inc
        return None

    def open_incidents(self) -> List[Incident]:
        return list(self._open.values())

    def closed_incidents(self) -> List[Incident]:
        return list(self._closed)

    def all_incidents(self) -> List[Incident]:
        return self.open_incidents() + self.closed_incidents()

    def get_open(self, job_name: str) -> Optional[Incident]:
        return self._open.get(job_name)
