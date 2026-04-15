"""Tests for cronwatch.reporter."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from cronwatch.tracker import JobRun, JobStatus
from cronwatch.reporter import JobSummary, summarise_runs, format_report


def _run(
    status: JobStatus,
    duration: float = 10.0,
    offset_minutes: int = 0,
) -> JobRun:
    started = datetime(2024, 1, 1, 12, 0, 0) + timedelta(minutes=offset_minutes)
    finished = started + timedelta(seconds=duration)
    return JobRun(
        job_name="backup",
        started_at=started,
        finished_at=finished,
        exit_code=0 if status == JobStatus.SUCCESS else 1,
        status=status,
    )


@pytest.fixture
def mixed_runs():
    return [
        _run(JobStatus.SUCCESS, duration=8.0, offset_minutes=0),
        _run(JobStatus.SUCCESS, duration=12.0, offset_minutes=5),
        _run(JobStatus.FAILURE, duration=3.0, offset_minutes=10),
        _run(JobStatus.TIMEOUT, duration=60.0, offset_minutes=15),
    ]


def test_summarise_runs_counts(mixed_runs):
    summary = summarise_runs("backup", mixed_runs)
    assert summary.total_runs == 4
    assert summary.successful_runs == 2
    assert summary.failed_runs == 1
    assert summary.timed_out_runs == 1


def test_summarise_runs_durations(mixed_runs):
    summary = summarise_runs("backup", mixed_runs)
    assert summary.min_duration_seconds == pytest.approx(3.0)
    assert summary.max_duration_seconds == pytest.approx(60.0)
    assert summary.avg_duration_seconds == pytest.approx((8 + 12 + 3 + 60) / 4)


def test_summarise_runs_success_rate(mixed_runs):
    summary = summarise_runs("backup", mixed_runs)
    assert summary.success_rate == pytest.approx(50.0)


def test_summarise_runs_last_status(mixed_runs):
    summary = summarise_runs("backup", mixed_runs)
    # offset_minutes=15 is the latest run — TIMEOUT
    assert summary.last_status == JobStatus.TIMEOUT


def test_summarise_runs_empty():
    summary = summarise_runs("noop", [])
    assert summary.total_runs == 0
    assert summary.success_rate is None
    assert summary.avg_duration_seconds is None
    assert summary.last_status is None


def test_summarise_runs_skips_running():
    running = JobRun(
        job_name="backup",
        started_at=datetime(2024, 1, 1, 12, 0),
        finished_at=None,
        exit_code=None,
        status=JobStatus.RUNNING,
    )
    summary = summarise_runs("backup", [running])
    assert summary.total_runs == 0


def test_format_report_contains_job_name(mixed_runs):
    summary = summarise_runs("backup", mixed_runs)
    report = format_report([summary])
    assert "backup" in report
    assert "50.0%" in report


def test_format_report_empty():
    report = format_report([])
    assert "No job data" in report
