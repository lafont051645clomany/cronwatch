"""Tests for cronwatch.scheduler."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from cronwatch.config import JobConfig
from cronwatch.scheduler import describe_schedule, is_overdue, next_run


@pytest.fixture()
def hourly_job() -> JobConfig:
    return JobConfig(name="hourly", schedule="0 * * * *", timeout_seconds=300)


@pytest.fixture()
def minutely_job() -> JobConfig:
    return JobConfig(name="minutely", schedule="* * * * *", timeout_seconds=60)


# ---------------------------------------------------------------------------
# next_run
# ---------------------------------------------------------------------------


def test_next_run_returns_future_datetime(hourly_job):
    after = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    result = next_run(hourly_job, after=after)
    assert result > after
    assert result.tzinfo == timezone.utc


def test_next_run_aligns_to_schedule(hourly_job):
    after = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    result = next_run(hourly_job, after=after)
    # Next whole hour after 10:30 is 11:00
    assert result == datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc)


def test_next_run_defaults_to_now(minutely_job):
    before = datetime.now(timezone.utc)
    result = next_run(minutely_job)
    after = datetime.now(timezone.utc)
    assert before < result <= after + timedelta(minutes=1)


# ---------------------------------------------------------------------------
# is_overdue
# ---------------------------------------------------------------------------


def test_not_overdue_when_just_started(hourly_job):
    now = datetime.now(timezone.utc)
    # Started 30 minutes ago; next run is ~30 min away — not overdue.
    last_started = now - timedelta(minutes=30)
    assert is_overdue(hourly_job, last_started) is False


def test_overdue_when_past_deadline(hourly_job):
    now = datetime.now(timezone.utc)
    # Started 90 minutes ago; next slot was 30 min ago, timeout=300 s (5 min).
    last_started = now - timedelta(minutes=90)
    assert is_overdue(hourly_job, last_started) is True


def test_not_overdue_within_timeout_window(hourly_job):
    now = datetime.now(timezone.utc)
    # Started 61 minutes ago; deadline = next_run + 300 s.
    # next_run ≈ now - 1 min; deadline ≈ now + 4 min → not overdue.
    last_started = now - timedelta(minutes=61)
    assert is_overdue(hourly_job, last_started) is False


# ---------------------------------------------------------------------------
# describe_schedule
# ---------------------------------------------------------------------------


def test_describe_known_schedule(hourly_job):
    assert describe_schedule(hourly_job) == "every hour"


def test_describe_unknown_schedule():
    job = JobConfig(name="custom", schedule="30 6 * * 2", timeout_seconds=60)
    assert describe_schedule(job) == "cron(30 6 * * 2)"


def test_describe_daily():
    job = JobConfig(name="nightly", schedule="0 0 * * *", timeout_seconds=120)
    assert describe_schedule(job) == "daily at midnight"
