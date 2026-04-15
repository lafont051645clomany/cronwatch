"""Tests for cronwatch.aggregator."""
from datetime import datetime, timezone

import pytest

from cronwatch.aggregator import Bucket, aggregate, _bucket_key
from cronwatch.tracker import JobRun, JobStatus


def _make_run(
    job: str,
    started: datetime,
    status: JobStatus = JobStatus.SUCCESS,
    finished: datetime | None = None,
) -> JobRun:
    run = JobRun(job_name=job, started_at=started)
    run.status = status
    run.finished_at = finished or started.replace(second=started.second + 5)
    return run


T = datetime(2024, 6, 1, 12, 30, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# _bucket_key
# ---------------------------------------------------------------------------

def test_bucket_key_minute():
    key = _bucket_key(T, "minute")
    assert key == T.replace(second=0, microsecond=0)


def test_bucket_key_hour():
    key = _bucket_key(T, "hour")
    assert key == T.replace(minute=0, second=0, microsecond=0)


def test_bucket_key_day():
    key = _bucket_key(T, "day")
    assert key == T.replace(hour=0, minute=0, second=0, microsecond=0)


# ---------------------------------------------------------------------------
# aggregate
# ---------------------------------------------------------------------------

@pytest.fixture()
def runs():
    base = datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
    return [
        _make_run("backup", base, JobStatus.SUCCESS),
        _make_run("backup", base.replace(minute=30), JobStatus.FAILED),
        _make_run("backup", base.replace(hour=11), JobStatus.SUCCESS),
        _make_run("sync", base, JobStatus.SUCCESS),
    ]


def test_aggregate_groups_by_job(runs):
    result = aggregate(runs, period="hour")
    assert set(result.keys()) == {"backup", "sync"}


def test_aggregate_backup_two_hourly_buckets(runs):
    result = aggregate(runs, period="hour")
    backup_buckets = result["backup"]
    assert len(backup_buckets) == 2


def test_aggregate_first_bucket_has_failure(runs):
    result = aggregate(runs, period="hour")
    first = result["backup"][0]
    assert first.total == 2
    assert first.failures == 1


def test_aggregate_success_rate(runs):
    result = aggregate(runs, period="hour")
    first = result["backup"][0]
    assert pytest.approx(first.success_rate) == 0.5


def test_aggregate_filter_by_job_name(runs):
    result = aggregate(runs, period="hour", job_name="sync")
    assert list(result.keys()) == ["sync"]


def test_aggregate_empty_returns_empty():
    assert aggregate([]) == {}


def test_aggregate_avg_duration_present(runs):
    result = aggregate(runs, period="hour")
    for buckets in result.values():
        for b in buckets:
            if b.durations:
                assert b.avg_duration is not None


def test_bucket_avg_duration_none_when_no_durations():
    b = Bucket(period_start=T)
    assert b.avg_duration is None


def test_bucket_success_rate_zero_when_empty():
    b = Bucket(period_start=T)
    assert b.success_rate == 0.0
