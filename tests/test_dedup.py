"""Tests for cronwatch.dedup and cronwatch.dedup_reporter."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronwatch.dedup import DedupConfig, DedupTracker
from cronwatch.dedup_reporter import format_dedup_table


def _utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2024, 1, 1, hour, minute, tzinfo=timezone.utc)


@pytest.fixture
def cfg() -> DedupConfig:
    return DedupConfig(window_seconds=60, max_suppressed=3)


@pytest.fixture
def tracker(cfg: DedupConfig) -> DedupTracker:
    return DedupTracker(cfg)


def test_first_occurrence_not_duplicate(tracker: DedupTracker) -> None:
    assert tracker.is_duplicate("backup", "failed", now=_utc(10)) is False


def test_after_record_is_duplicate(tracker: DedupTracker) -> None:
    tracker.record("backup", "failed", now=_utc(10))
    assert tracker.is_duplicate("backup", "failed", now=_utc(10, 1)) is True


def test_window_expiry_clears_duplicate(tracker: DedupTracker) -> None:
    tracker.record("backup", "failed", now=_utc(10))
    # 2 minutes later — beyond 60s window
    assert tracker.is_duplicate("backup", "failed", now=_utc(10, 2)) is False


def test_exceeds_max_suppressed_stops_suppressing(tracker: DedupTracker) -> None:
    # max_suppressed=3: after 3 records, suppression stops
    t = _utc(10)
    tracker.record("backup", "failed", now=t)
    tracker.record("backup", "failed", now=t)
    tracker.record("backup", "failed", now=t)
    assert tracker.is_duplicate("backup", "failed", now=t) is False


def test_record_returns_incremented_count(tracker: DedupTracker) -> None:
    t = _utc(10)
    assert tracker.record("sync", "timeout", now=t) == 1
    assert tracker.record("sync", "timeout", now=t) == 2
    assert tracker.record("sync", "timeout", now=t) == 3


def test_get_count_zero_when_no_entry(tracker: DedupTracker) -> None:
    assert tracker.get_count("nonexistent", "failed") == 0


def test_get_count_reflects_records(tracker: DedupTracker) -> None:
    tracker.record("job", "failed", now=_utc(10))
    tracker.record("job", "failed", now=_utc(10))
    assert tracker.get_count("job", "failed") == 2


def test_reset_clears_entry(tracker: DedupTracker) -> None:
    tracker.record("job", "failed", now=_utc(10))
    tracker.reset("job", "failed")
    assert tracker.get_count("job", "failed") == 0
    assert tracker.is_duplicate("job", "failed", now=_utc(10)) is False


def test_different_statuses_tracked_independently(tracker: DedupTracker) -> None:
    t = _utc(10)
    tracker.record("job", "failed", now=t)
    assert tracker.is_duplicate("job", "timeout", now=t) is False
    assert tracker.is_duplicate("job", "failed", now=t) is True


# --- reporter tests ---


def test_empty_pairs_returns_message(tracker: DedupTracker) -> None:
    result = format_dedup_table(tracker, [])
    assert "No dedup entries" in result


def test_table_contains_job_name(tracker: DedupTracker) -> None:
    tracker.record("nightly-backup", "failed", now=_utc(10))
    result = format_dedup_table(tracker, [("nightly-backup", "failed")])
    assert "nightly-backup" in result


def test_table_shows_suppressing_yes(tracker: DedupTracker) -> None:
    tracker.record("nightly-backup", "failed", now=_utc(10))
    result = format_dedup_table(tracker, [("nightly-backup", "failed")])
    assert "yes" in result


def test_table_shows_suppressing_no_for_fresh(tracker: DedupTracker) -> None:
    result = format_dedup_table(tracker, [("fresh-job", "failed")])
    assert "no" in result
