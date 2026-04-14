"""Tests for cronwatch.tracker."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from cronwatch.config import JobConfig
from cronwatch.tracker import JobRun, JobStatus, JobTracker


@pytest.fixture()
def tracker() -> JobTracker:
    return JobTracker()


def test_start_creates_active_run(tracker):
    run = tracker.start("backup")
    assert run.job_name == "backup"
    assert run.status == JobStatus.RUNNING
    assert "backup" in tracker.active


def test_finish_success(tracker):
    tracker.start("backup")
    run = tracker.finish("backup", exit_code=0)
    assert run is not None
    assert run.status == JobStatus.SUCCESS
    assert run.exit_code == 0
    assert "backup" not in tracker.active
    assert run in tracker.history


def test_finish_failure(tracker):
    tracker.start("backup")
    run = tracker.finish("backup", exit_code=1)
    assert run.status == JobStatus.FAILED


def test_finish_unknown_job_returns_none(tracker):
    result = tracker.finish("nonexistent", exit_code=0)
    assert result is None


def test_duration_seconds(tracker):
    run = tracker.start("backup")
    run.finished_at = run.started_at + timedelta(seconds=42)
    assert run.duration_seconds == pytest.approx(42.0)


def test_duration_seconds_none_when_running(tracker):
    run = tracker.start("backup")
    assert run.duration_seconds is None


def test_check_timeouts_detects_overdue(tracker):
    job_cfg = {"backup": JobConfig(name="backup", schedule="0 2 * * *", max_duration=60)}
    run = tracker.start("backup")
    # Simulate run started 2 minutes ago
    run.started_at = datetime.utcnow() - timedelta(seconds=120)
    timed_out = tracker.check_timeouts(job_cfg)
    assert len(timed_out) == 1
    assert timed_out[0].status == JobStatus.TIMEOUT


def test_check_timeouts_ignores_within_limit(tracker):
    job_cfg = {"backup": JobConfig(name="backup", schedule="0 2 * * *", max_duration=3600)}
    tracker.start("backup")
    timed_out = tracker.check_timeouts(job_cfg)
    assert timed_out == []


def test_check_timeouts_ignores_jobs_without_max_duration(tracker):
    job_cfg = {"backup": JobConfig(name="backup", schedule="0 2 * * *", max_duration=None)}
    run = tracker.start("backup")
    run.started_at = datetime.utcnow() - timedelta(seconds=9999)
    timed_out = tracker.check_timeouts(job_cfg)
    assert timed_out == []
