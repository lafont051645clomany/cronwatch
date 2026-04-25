"""Tests for cronwatch.grouping and cronwatch.grouping_reporter."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pytest

from cronwatch.tracker import JobRun, JobStatus
from cronwatch.grouping import (
    RunGroup,
    group_by,
    group_by_job,
    group_by_status,
    group_by_date,
)
from cronwatch.grouping_reporter import format_group_table


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def _run(
    job: str,
    status: JobStatus,
    started: Optional[datetime] = None,
    duration: Optional[float] = None,
) -> JobRun:
    finished = None
    if started is not None and duration is not None:
        from datetime import timedelta
        finished = started + timedelta(seconds=duration)
    return JobRun(
        job_name=job,
        status=status,
        started_at=started,
        finished_at=finished,
    )


@pytest.fixture()
def mixed_runs():
    return [
        _run("backup", JobStatus.SUCCESS, _utc(2024, 1, 1), 30.0),
        _run("backup", JobStatus.FAILURE, _utc(2024, 1, 2), 5.0),
        _run("sync", JobStatus.SUCCESS, _utc(2024, 1, 1), 10.0),
        _run("sync", JobStatus.SUCCESS, _utc(2024, 1, 2), 20.0),
        _run("cleanup", JobStatus.FAILURE, _utc(2024, 1, 1), 2.0),
    ]


def test_group_by_job_keys(mixed_runs):
    groups = group_by_job(mixed_runs)
    assert set(groups.keys()) == {"backup", "sync", "cleanup"}


def test_group_by_job_counts(mixed_runs):
    groups = group_by_job(mixed_runs)
    assert groups["backup"].count == 2
    assert groups["sync"].count == 2
    assert groups["cleanup"].count == 1


def test_group_by_job_failure_count(mixed_runs):
    groups = group_by_job(mixed_runs)
    assert groups["backup"].failure_count == 1
    assert groups["sync"].failure_count == 0


def test_group_by_job_success_rate(mixed_runs):
    groups = group_by_job(mixed_runs)
    assert groups["sync"].success_rate == pytest.approx(1.0)
    assert groups["backup"].success_rate == pytest.approx(0.5)
    assert groups["cleanup"].success_rate == pytest.approx(0.0)


def test_group_by_job_avg_duration(mixed_runs):
    groups = group_by_job(mixed_runs)
    assert groups["sync"].avg_duration == pytest.approx(15.0)


def test_group_by_status(mixed_runs):
    groups = group_by_status(mixed_runs)
    assert groups[JobStatus.SUCCESS.value].count == 3
    assert groups[JobStatus.FAILURE.value].count == 2


def test_group_by_date(mixed_runs):
    groups = group_by_date(mixed_runs)
    assert groups["2024-01-01"].count == 3
    assert groups["2024-01-02"].count == 2


def test_group_by_skips_none_keys():
    runs = [
        _run("job", JobStatus.SUCCESS, None),  # no started_at → date key is None
        _run("job", JobStatus.SUCCESS, _utc(2024, 3, 1)),
    ]
    groups = group_by_date(runs)
    assert len(groups) == 1


def test_run_group_empty_stats():
    g = RunGroup(key="empty")
    assert g.count == 0
    assert g.success_rate is None
    assert g.avg_duration is None


def test_format_group_table_empty():
    result = format_group_table({})
    assert "No groups" in result


def test_format_group_table_contains_keys(mixed_runs):
    groups = group_by_job(mixed_runs)
    table = format_group_table(groups)
    assert "backup" in table
    assert "sync" in table
    assert "cleanup" in table


def test_format_group_table_contains_rates(mixed_runs):
    groups = group_by_job(mixed_runs)
    table = format_group_table(groups)
    assert "100.0%" in table  # sync
    assert "50.0%" in table   # backup
    assert "0.0%" in table    # cleanup
