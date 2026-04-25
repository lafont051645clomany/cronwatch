"""Tests for cronwatch.replay_reporter."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from cronwatch.tracker import JobRun, JobStatus
from cronwatch.replay import replay_run, replay_many, ReplayResult
from cronwatch.replay_reporter import format_replay_table


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def _result(status: JobStatus, dispatched: bool = True) -> ReplayResult:
    run = JobRun(job_name="nightly-sync")
    run.status = status
    run.start_time = _utc(2024, 3, 10, 2, 0, 0)
    run.end_time = _utc(2024, 3, 10, 2, 10, 0)
    notes = ["dispatched" if dispatched else "skipped: status did not meet dispatch criteria"]
    return ReplayResult(run=run, dispatched=dispatched, notes=notes)


def test_empty_returns_message():
    out = format_replay_table([])
    assert "No replay results" in out


def test_table_contains_job_name():
    out = format_replay_table([_result(JobStatus.FAILURE)])
    assert "nightly-sync" in out


def test_table_contains_status():
    out = format_replay_table([_result(JobStatus.FAILURE)])
    assert "failure" in out.lower()


def test_dispatched_yes_shown():
    out = format_replay_table([_result(JobStatus.FAILURE, dispatched=True)])
    assert "yes" in out


def test_dispatched_no_shown():
    out = format_replay_table([_result(JobStatus.SUCCESS, dispatched=False)])
    assert "no" in out


def test_summary_line_counts():
    results = [
        _result(JobStatus.FAILURE, dispatched=True),
        _result(JobStatus.SUCCESS, dispatched=False),
        _result(JobStatus.TIMEOUT, dispatched=True),
    ]
    out = format_replay_table(results)
    assert "Total: 3" in out
    assert "Dispatched: 2" in out
    assert "Suppressed: 1" in out


def test_notes_appear_in_output():
    result = _result(JobStatus.FAILURE, dispatched=True)
    result.notes = ["dispatched run abc for job 'nightly-sync'"]
    out = format_replay_table([result])
    assert "dispatched run abc" in out
