"""Tests for cronwatch.replay."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from unittest.mock import MagicMock

import pytest

from cronwatch.tracker import JobRun, JobStatus
from cronwatch.replay import replay_run, replay_many, ReplayResult


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def _run(status: JobStatus, job: str = "backup") -> JobRun:
    run = JobRun(job_name=job)
    run.start_time = _utc(2024, 1, 1, 6, 0, 0)
    run.end_time = _utc(2024, 1, 1, 6, 5, 0)
    run.status = status
    return run


# ---------------------------------------------------------------------------
# replay_run
# ---------------------------------------------------------------------------

def test_replay_dispatches_failure():
    dispatch = MagicMock()
    result = replay_run(_run(JobStatus.FAILURE), dispatch)
    dispatch.assert_called_once()
    assert result.dispatched is True


def test_replay_dispatches_timeout():
    dispatch = MagicMock()
    result = replay_run(_run(JobStatus.TIMEOUT), dispatch)
    dispatch.assert_called_once()
    assert result.dispatched is True


def test_replay_skips_success():
    dispatch = MagicMock()
    result = replay_run(_run(JobStatus.SUCCESS), dispatch)
    dispatch.assert_not_called()
    assert result.dispatched is False
    assert any("skipped" in n for n in result.notes)


def test_dry_run_suppresses_dispatch():
    dispatch = MagicMock()
    result = replay_run(_run(JobStatus.FAILURE), dispatch, dry_run=True)
    dispatch.assert_not_called()
    assert result.dispatched is False
    assert any("dry-run" in n for n in result.notes)


def test_custom_should_dispatch_predicate():
    dispatch = MagicMock()
    # Only dispatch successes (unusual, but tests the hook)
    result = replay_run(
        _run(JobStatus.SUCCESS),
        dispatch,
        should_dispatch=lambda r: r.status == JobStatus.SUCCESS,
    )
    dispatch.assert_called_once()
    assert result.dispatched is True


def test_notes_contain_run_id_on_dispatch():
    dispatch = MagicMock()
    run = _run(JobStatus.FAILURE)
    result = replay_run(run, dispatch)
    assert run.run_id in " ".join(result.notes)


# ---------------------------------------------------------------------------
# replay_many
# ---------------------------------------------------------------------------

def test_replay_many_returns_one_result_per_run():
    runs = [_run(JobStatus.FAILURE), _run(JobStatus.SUCCESS), _run(JobStatus.TIMEOUT)]
    results = replay_many(runs, MagicMock())
    assert len(results) == 3


def test_replay_many_dry_run_dispatches_none():
    runs = [_run(JobStatus.FAILURE), _run(JobStatus.TIMEOUT)]
    dispatch = MagicMock()
    results = replay_many(runs, dispatch, dry_run=True)
    assert dispatch.call_count == 0
    assert all(not r.dispatched for r in results)
