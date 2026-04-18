"""Tests for cronwatch.quota and cronwatch.quota_reporter."""
from datetime import datetime, timedelta

import pytest

from cronwatch.quota import QuotaConfig, QuotaTracker
from cronwatch.quota_reporter import format_quota_table


@pytest.fixture()
def cfg() -> QuotaConfig:
    return QuotaConfig(max_runs=3, period_seconds=60)


@pytest.fixture()
def tracker() -> QuotaTracker:
    return QuotaTracker()


def test_initial_count_is_zero(tracker, cfg):
    assert tracker.count("backup", cfg) == 0


def test_record_increments_count(tracker, cfg):
    now = datetime.utcnow()
    tracker.record("backup", at=now)
    tracker.record("backup", at=now)
    assert tracker.count("backup", cfg, now=now) == 2


def test_old_records_evicted(tracker, cfg):
    old = datetime.utcnow() - timedelta(seconds=120)
    now = datetime.utcnow()
    tracker.record("backup", at=old)
    tracker.record("backup", at=now)
    assert tracker.count("backup", cfg, now=now) == 1


def test_is_exceeded_false_when_under_limit(tracker, cfg):
    now = datetime.utcnow()
    for _ in range(3):
        tracker.record("backup", at=now)
    assert not tracker.is_exceeded("backup", cfg, now=now)


def test_is_exceeded_true_when_over_limit(tracker, cfg):
    now = datetime.utcnow()
    for _ in range(4):
        tracker.record("backup", at=now)
    assert tracker.is_exceeded("backup", cfg, now=now)


def test_remaining_decreases_with_records(tracker, cfg):
    now = datetime.utcnow()
    assert tracker.remaining("backup", cfg, now=now) == 3
    tracker.record("backup", at=now)
    assert tracker.remaining("backup", cfg, now=now) == 2


def test_remaining_never_negative(tracker, cfg):
    now = datetime.utcnow()
    for _ in range(10):
        tracker.record("backup", at=now)
    assert tracker.remaining("backup", cfg, now=now) == 0


# --- reporter ---

def test_format_quota_table_empty():
    result = format_quota_table([], QuotaTracker())
    assert "No quota" in result


def test_format_quota_table_contains_job(tracker, cfg):
    now = datetime.utcnow()
    tracker.record("sync", at=now)
    result = format_quota_table([("sync", cfg)], tracker)
    assert "sync" in result
    assert "3" in result


def test_format_quota_table_shows_used(tracker, cfg):
    now = datetime.utcnow()
    tracker.record("sync", at=now)
    tracker.record("sync", at=now)
    result = format_quota_table([("sync", cfg)], tracker)
    assert "2" in result
