"""Snapshot module: capture and compare job state at a point in time."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from cronwatch.tracker import JobRun, JobStatus


@dataclass
class JobSnapshot:
    """A point-in-time summary of a single job's state."""

    job_name: str
    captured_at: datetime
    last_status: Optional[str]
    last_run_start: Optional[datetime]
    last_run_end: Optional[datetime]
    total_runs: int
    failure_count: int

    @property
    def success_rate(self) -> Optional[float]:
        if self.total_runs == 0:
            return None
        return (self.total_runs - self.failure_count) / self.total_runs


def capture(job_name: str, runs: List[JobRun]) -> JobSnapshot:
    """Build a snapshot for *job_name* from a list of completed runs."""
    job_runs = [r for r in runs if r.job_name == job_name]
    last: Optional[JobRun] = job_runs[-1] if job_runs else None
    failures = sum(1 for r in job_runs if r.status == JobStatus.FAILED)
    return JobSnapshot(
        job_name=job_name,
        captured_at=datetime.utcnow(),
        last_status=last.status.value if last else None,
        last_run_start=last.started_at if last else None,
        last_run_end=last.finished_at if last else None,
        total_runs=len(job_runs),
        failure_count=failures,
    )


def diff_snapshots(old: JobSnapshot, new: JobSnapshot) -> Dict[str, tuple]:
    """Return a dict of fields that changed between *old* and *new* snapshots.

    Each value is a ``(old_value, new_value)`` tuple.  Only scalar fields are
    compared; ``captured_at`` is intentionally excluded as it always differs.
    """
    fields = ("last_status", "last_run_start", "last_run_end", "total_runs", "failure_count")
    return {
        field: (getattr(old, field), getattr(new, field))
        for field in fields
        if getattr(old, field) != getattr(new, field)
    }


def _snap_to_dict(snap: JobSnapshot) -> dict:
    d = asdict(snap)
    d["captured_at"] = snap.captured_at.isoformat()
    d["last_run_start"] = snap.last_run_start.isoformat() if snap.last_run_start else None
    d["last_run_end"] = snap.last_run_end.isoformat() if snap.last_run_end else None
    return d


def _snap_from_dict(d: dict) -> JobSnapshot:
    def _dt(v: Optional[str]) -> Optional[datetime]:
        return datetime.fromisoformat(v) if v else None

    return JobSnapshot(
        job_name=d["job_name"],
        captured_at=datetime.fromisoformat(d["captured_at"]),
        last_status=d.get("last_status"),
        last_run_start=_dt(d.get("last_run_start")),
        last_run_end=_dt(d.get("last_run_end")),
        total_runs=d.get("total_runs", 0),
        failure_count=d.get("failure_count", 0),
    )


def save_snapshots(snapshots: Dict[str, JobSnapshot], path: Path) -> None:
    """Persist a mapping of job_name -> snapshot to *path* as JSON."""
    data = {name: _snap_to_dict(snap) for name, snap in snapshots.items()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def load_snapshots(path: Path) -> Dict[str, JobSnapshot]:
    """Load snapshots from *path*; returns empty dict if file absent."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {name: _snap_from_dict(v) for name, v in data.items()}
