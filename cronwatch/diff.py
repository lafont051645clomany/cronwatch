"""Diff module: compare two snapshots and surface meaningful changes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from cronwatch.snapshot import JobSnapshot


@dataclass
class SnapshotDiff:
    """Describes what changed for a single job between two snapshots."""

    job_name: str
    status_changed: bool
    previous_status: Optional[str]
    current_status: Optional[str]
    run_count_delta: int          # positive = more runs since last snapshot
    new_failures: int             # additional failures recorded
    is_new_job: bool              # job not present in baseline
    is_missing_job: bool          # job present in baseline but gone now

    @property
    def has_changes(self) -> bool:
        return (
            self.status_changed
            or self.run_count_delta != 0
            or self.new_failures != 0
            or self.is_new_job
            or self.is_missing_job
        )


def diff_snapshots(
    baseline: Dict[str, JobSnapshot],
    current: Dict[str, JobSnapshot],
) -> List[SnapshotDiff]:
    """Return a list of diffs for every job that appears in either mapping."""
    all_names = set(baseline) | set(current)
    diffs: List[SnapshotDiff] = []

    for name in sorted(all_names):
        old = baseline.get(name)
        new = current.get(name)

        if old is None and new is not None:
            diffs.append(
                SnapshotDiff(
                    job_name=name,
                    status_changed=True,
                    previous_status=None,
                    current_status=new.last_status,
                    run_count_delta=new.total_runs,
                    new_failures=new.failure_count,
                    is_new_job=True,
                    is_missing_job=False,
                )
            )
        elif old is not None and new is None:
            diffs.append(
                SnapshotDiff(
                    job_name=name,
                    status_changed=True,
                    previous_status=old.last_status,
                    current_status=None,
                    run_count_delta=0,
                    new_failures=0,
                    is_new_job=False,
                    is_missing_job=True,
                )
            )
        else:
            assert old is not None and new is not None
            diffs.append(
                SnapshotDiff(
                    job_name=name,
                    status_changed=old.last_status != new.last_status,
                    previous_status=old.last_status,
                    current_status=new.last_status,
                    run_count_delta=new.total_runs - old.total_runs,
                    new_failures=max(0, new.failure_count - old.failure_count),
                    is_new_job=False,
                    is_missing_job=False,
                )
            )

    return diffs


def changed_only(diffs: List[SnapshotDiff]) -> List[SnapshotDiff]:
    """Filter to diffs that actually have something noteworthy."""
    return [d for d in diffs if d.has_changes]
