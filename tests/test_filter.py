"""Tests for cronwatch.filter."""

from datetime import datetime, timezone

import pytest

from cronwatch.tracker import JobRun, JobStatus
from cronwatch.filter import (
    apply_filters,
    by_job_name,
    by_predicate,
    by_status,
    by_time_range,
)


def _make_run(
    name: str,
    status: JobStatus = JobStatus.SUCCESS,
    started_at: datetime | None = None,
) -> JobRun:
    started_at = started_at or datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    run = JobRun(job_name=name, started_at=started_at)
    run.status = status
    return run


@pytest.fixture()
def runs():
    return [
        _make_run("backup", JobStatus.SUCCESS, datetime(2024, 1, 15, 8, 0, tzinfo=timezone.utc)),
        _make_run("backup", JobStatus.FAILURE, datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc)),
        _make_run("cleanup", JobStatus.SUCCESS, datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)),
        _make_run("cleanup", JobStatus.TIMEOUT, datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc)),
        _make_run("report", JobStatus.SUCCESS, datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)),
    ]


def test_by_job_name_returns_matching(runs):
    result = by_job_name(runs, "backup")
    assert len(result) == 2
    assert all(r.job_name == "backup" for r in result)


def test_by_job_name_case_insensitive(runs):
    result = by_job_name(runs, "BACKUP")
    assert len(result) == 2


def test_by_job_name_no_match_returns_empty(runs):
    assert by_job_name(runs, "nonexistent") == []


def test_by_status_success(runs):
    result = by_status(runs, JobStatus.SUCCESS)
    assert len(result) == 3


def test_by_status_failure(runs):
    result = by_status(runs, JobStatus.FAILURE)
    assert len(result) == 1
    assert result[0].job_name == "backup"


def test_by_time_range_since_only(runs):
    since = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
    result = by_time_range(runs, since=since)
    assert len(result) == 3


def test_by_time_range_until_only(runs):
    until = datetime(2024, 1, 15, 9, 30, tzinfo=timezone.utc)
    result = by_time_range(runs, until=until)
    assert len(result) == 2


def test_by_time_range_both_bounds(runs):
    since = datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc)
    until = datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc)
    result = by_time_range(runs, since=since, until=until)
    assert len(result) == 3


def test_by_predicate(runs):
    result = by_predicate(runs, lambda r: r.job_name == "cleanup" and r.status == JobStatus.TIMEOUT)
    assert len(result) == 1
    assert result[0].status == JobStatus.TIMEOUT


def test_apply_filters_combined(runs):
    since = datetime(2024, 1, 15, 8, 30, tzinfo=timezone.utc)
    result = apply_filters(runs, job_name="backup", status=JobStatus.FAILURE, since=since)
    assert len(result) == 1
    assert result[0].status == JobStatus.FAILURE


def test_apply_filters_no_criteria_returns_all(runs):
    result = apply_filters(runs)
    assert len(result) == len(runs)
