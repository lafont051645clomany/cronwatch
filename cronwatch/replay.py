"""Replay — re-run a historical JobRun through alert/hook pipelines for testing."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from cronwatch.tracker import JobRun, JobStatus


@dataclass
class ReplayResult:
    run: JobRun
    dispatched: bool
    notes: List[str] = field(default_factory=list)


def _default_should_dispatch(run: JobRun) -> bool:
    """Dispatch if the run failed or timed-out."""
    return run.status in (JobStatus.FAILURE, JobStatus.TIMEOUT)


def replay_run(
    run: JobRun,
    dispatch_fn: Callable[[JobRun], None],
    *,
    should_dispatch: Optional[Callable[[JobRun], bool]] = None,
    dry_run: bool = False,
) -> ReplayResult:
    """Replay *run* through *dispatch_fn*.

    Args:
        run:             The historical :class:`~cronwatch.tracker.JobRun` to replay.
        dispatch_fn:     Callable that accepts a :class:`~cronwatch.tracker.JobRun`
                         and performs the actual alert/hook dispatch.
        should_dispatch: Optional predicate; defaults to dispatching on failure/timeout.
        dry_run:         When *True* the dispatch is skipped but the result is recorded.

    Returns:
        A :class:`ReplayResult` describing what happened.
    """
    predicate = should_dispatch or _default_should_dispatch
    notes: List[str] = []

    if not predicate(run):
        notes.append(f"skipped: status '{run.status.value}' did not meet dispatch criteria")
        return ReplayResult(run=run, dispatched=False, notes=notes)

    if dry_run:
        notes.append("dry-run: dispatch suppressed")
        return ReplayResult(run=run, dispatched=False, notes=notes)

    dispatch_fn(run)
    notes.append(f"dispatched run {run.run_id} for job '{run.job_name}'")
    return ReplayResult(run=run, dispatched=True, notes=notes)


def replay_many(
    runs: List[JobRun],
    dispatch_fn: Callable[[JobRun], None],
    *,
    should_dispatch: Optional[Callable[[JobRun], bool]] = None,
    dry_run: bool = False,
) -> List[ReplayResult]:
    """Replay a list of runs, returning one :class:`ReplayResult` per run."""
    return [
        replay_run(run, dispatch_fn, should_dispatch=should_dispatch, dry_run=dry_run)
        for run in runs
    ]
