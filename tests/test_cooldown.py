"""Tests for cronwatch.cooldown."""

from datetime import datetime, timezone, timedelta

import pytest

from cronwatch.cooldown import CooldownConfig, CooldownTracker


def _utc(offset_seconds: float = 0) -> datetime:
    base = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    return base + timedelta(seconds=offset_seconds)


@pytest.fixture()
def cfg() -> CooldownConfig:
    return CooldownConfig(period_seconds=300, max_alerts=1)


@pytest.fixture()
def tracker(cfg: CooldownConfig) -> CooldownTracker:
    return CooldownTracker(cfg)


# ---------------------------------------------------------------------------
# is_allowed
# ---------------------------------------------------------------------------

def test_first_alert_always_allowed(tracker: CooldownTracker) -> None:
    assert tracker.is_allowed("backup", at=_utc()) is True


def test_second_alert_within_period_blocked(tracker: CooldownTracker) -> None:
    tracker.record("backup", at=_utc(0))
    assert tracker.is_allowed("backup", at=_utc(100)) is False


def test_alert_allowed_after_period_expires(tracker: CooldownTracker) -> None:
    tracker.record("backup", at=_utc(0))
    assert tracker.is_allowed("backup", at=_utc(300)) is True


def test_alert_allowed_just_after_period(tracker: CooldownTracker) -> None:
    tracker.record("backup", at=_utc(0))
    assert tracker.is_allowed("backup", at=_utc(301)) is True


def test_different_jobs_are_independent(tracker: CooldownTracker) -> None:
    tracker.record("backup", at=_utc(0))
    assert tracker.is_allowed("cleanup", at=_utc(10)) is True


def test_max_alerts_zero_allows_multiple_within_period() -> None:
    """max_alerts=0 means unlimited alerts are allowed (no cap)."""
    t = CooldownTracker(CooldownConfig(period_seconds=300, max_alerts=0))
    t.record("job", at=_utc(0))
    # With max_alerts=0 the cap branch is never triggered; still blocked by period.
    assert t.is_allowed("job", at=_utc(100)) is False


def test_max_alerts_two_allows_second_within_period() -> None:
    t = CooldownTracker(CooldownConfig(period_seconds=300, max_alerts=2))
    t.record("job", at=_utc(0))
    assert t.is_allowed("job", at=_utc(50)) is True
    t.record("job", at=_utc(50))
    assert t.is_allowed("job", at=_utc(100)) is False


# ---------------------------------------------------------------------------
# record
# ---------------------------------------------------------------------------

def test_record_creates_entry(tracker: CooldownTracker) -> None:
    tracker.record("sync", at=_utc(0))
    entry = tracker.status("sync")
    assert entry is not None
    assert entry.count == 1


def test_record_increments_count_within_period(tracker: CooldownTracker) -> None:
    t = CooldownTracker(CooldownConfig(period_seconds=300, max_alerts=5))
    t.record("sync", at=_utc(0))
    t.record("sync", at=_utc(60))
    assert t.status("sync").count == 2  # type: ignore[union-attr]


def test_record_resets_window_after_period(tracker: CooldownTracker) -> None:
    tracker.record("sync", at=_utc(0))
    tracker.record("sync", at=_utc(400))  # past the 300 s window
    entry = tracker.status("sync")
    assert entry is not None
    assert entry.count == 1


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

def test_reset_clears_entry(tracker: CooldownTracker) -> None:
    tracker.record("sync", at=_utc(0))
    tracker.reset("sync")
    assert tracker.status("sync") is None
    assert tracker.is_allowed("sync", at=_utc(10)) is True


def test_reset_unknown_job_is_noop(tracker: CooldownTracker) -> None:
    tracker.reset("nonexistent")  # should not raise
    assert tracker.status("nonexistent") is None
