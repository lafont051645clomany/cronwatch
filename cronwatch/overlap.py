"""Detect overlapping job runs — runs that started before a previous run finished."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronwatch.tracker import JobRun, JobStatus


@dataclass
class OverlapRecord:
    job_name: str
    earlier_run_id: str
    later_run_id: str
    overlap_seconds: float
    earlier_started: object  # datetime
    later_started: object   # datetime

    @property
    def message(self) -> str:
        return (
            f"Job '{self.job_name}' overlap: run {self.later_run_id} started "
            f"{self.overlap_seconds:.1f}s before run {self.earlier_run_id} finished."
        )


def _finished_at(run: JobRun) -> Optional[object]:
    """Return finished_at if available, else None."""
    return getattr(run, "finished_at", None)


def detect_overlaps(runs: List[JobRun]) -> List[OverlapRecord]:
    """Return overlap records for all runs of the same job that overlap in time.

    Only completed runs (with a ``finished_at`` timestamp) are considered as
    the *earlier* run.  Any run whose ``started_at`` falls before the earlier
    run's ``finished_at`` is flagged.
    """
    by_job: dict[str, List[JobRun]] = {}
    for run in runs:
        if run.started_at is None:
            continue
        by_job.setdefault(run.job_name, []).append(run)

    records: List[OverlapRecord] = []

    for job_name, job_runs in by_job.items():
        # Sort by start time
        sorted_runs = sorted(job_runs, key=lambda r: r.started_at)
        for i, earlier in enumerate(sorted_runs):
            finished = _finished_at(earlier)
            if finished is None:
                continue
            for later in sorted_runs[i + 1 :]:
                if later.started_at >= finished:
                    break  # sorted, so no further overlap possible
                overlap_secs = (finished - later.started_at).total_seconds()
                records.append(
                    OverlapRecord(
                        job_name=job_name,
                        earlier_run_id=earlier.run_id,
                        later_run_id=later.run_id,
                        overlap_seconds=overlap_secs,
                        earlier_started=earlier.started_at,
                        later_started=later.started_at,
                    )
                )

    return records


def format_overlap_table(records: List[OverlapRecord]) -> str:
    """Return a human-readable table of overlap records."""
    if not records:
        return "No overlapping runs detected."

    header = f"{'Job':<20} {'Earlier Run':<36} {'Later Run':<36} {'Overlap (s)':>12}"
    sep = "-" * len(header)
    rows = [
        f"{r.job_name:<20} {r.earlier_run_id:<36} {r.later_run_id:<36} {r.overlap_seconds:>12.1f}"
        for r in records
    ]
    return "\n".join([header, sep] + rows)
