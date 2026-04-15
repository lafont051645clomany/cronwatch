"""Tests for cronwatch.formatter."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronwatch.formatter import (
    format_run_table,
    format_summary_table,
    _fmt_duration,
    _fmt_dt,
)
from cronwatch.reporter import JobSummary
from cronwatch.tracker import JobRun, JobStatus


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _run(name: str, status: JobStatus, duration: float | None = None) -> JobRun:
    r = JobRun(job_name=name)
    r.started_at = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    r.status = status
    r.duration_seconds = duration
    return r


def _summary(
    name: str,
    total: int = 10,
    ok: int = 8,
    fail: int = 2,
    avg: float = 30.0,
    max_: float = 60.0,
) -> JobSummary:
    return JobSummary(
        job_name=name,
        total_runs=total,
        successful=ok,
        failed=fail,
        avg_duration=avg,
        max_duration=max_,
    )


# ---------------------------------------------------------------------------
# _fmt_duration
# ---------------------------------------------------------------------------

def test_fmt_duration_none():
    assert _fmt_duration(None) == "—"


def test_fmt_duration_seconds():
    assert _fmt_duration(45.5) == "45.5s"


def test_fmt_duration_minutes():
    assert _fmt_duration(90.0) == "1m 30s"


# ---------------------------------------------------------------------------
# _fmt_dt
# ---------------------------------------------------------------------------

def test_fmt_dt_none():
    assert _fmt_dt(None) == "—"


def test_fmt_dt_aware():
    dt = datetime(2024, 1, 15, 9, 5, 3, tzinfo=timezone.utc)
    assert _fmt_dt(dt) == "2024-01-15 09:05:03 UTC"


def test_fmt_dt_naive_treated_as_utc():
    dt = datetime(2024, 1, 15, 9, 5, 3)
    result = _fmt_dt(dt)
    assert "2024-01-15" in result


# ---------------------------------------------------------------------------
# format_run_table
# ---------------------------------------------------------------------------

def test_format_run_table_empty():
    assert format_run_table([]) == "No runs recorded."


def test_format_run_table_contains_job_name():
    runs = [_run("backup-job", JobStatus.SUCCESS, 42.0)]
    table = format_run_table(runs)
    assert "backup-job" in table
    assert "success" in table
    assert "42.0s" in table


def test_format_run_table_multiple_rows():
    runs = [
        _run("job-a", JobStatus.SUCCESS, 10.0),
        _run("job-b", JobStatus.FAILURE, None),
    ]
    table = format_run_table(runs)
    assert "job-a" in table
    assert "job-b" in table


# ---------------------------------------------------------------------------
# format_summary_table
# ---------------------------------------------------------------------------

def test_format_summary_table_empty():
    assert format_summary_table([]) == "No job summaries available."


def test_format_summary_table_contains_fields():
    summaries = [_summary("nightly-sync")]
    table = format_summary_table(summaries)
    assert "nightly-sync" in table
    assert "80.0%" in table
    assert "30.0s" in table
