"""Tests for cronwatch.anomaly."""
from datetime import datetime, timedelta

import pytest

from cronwatch.anomaly import AnomalyTracker
from cronwatch.tracker import JobRun, JobStatus


def _run(name: str = "backup") -> JobRun:
    return JobRun(
        job_name=name,
        started_at=datetime(2024, 1, 1, 12, 0, 0),
        status=JobStatus.FAILED,
    )


@pytest.fixture
def tracker() -> AnomalyTracker:
    return AnomalyTracker(window=timedelta(hours=1), threshold=3)


def test_first_occurrence_fires(tracker):
    assert tracker.record(_run()) is True


def test_second_occurrence_fires(tracker):
    now = datetime(2024, 1, 1, 12, 0, 0)
    tracker.record(_run(), now=now)
    assert tracker.record(_run(), now=now) is True


def test_exceeds_threshold_suppresses(tracker):
    now = datetime(2024, 1, 1, 12, 0, 0)
    for _ in range(3):
        tracker.record(_run(), now=now)
    result = tracker.record(_run(), now=now)
    assert result is False


def test_suppressed_count_increments(tracker):
    now = datetime(2024, 1, 1, 12, 0, 0)
    for _ in range(4):
        tracker.record(_run(), now=now)
    rec = tracker.get("backup")
    assert rec.suppressed == 1


def test_eviction_after_window(tracker):
    t0 = datetime(2024, 1, 1, 12, 0, 0)
    for _ in range(4):
        tracker.record(_run(), now=t0)
    t1 = t0 + timedelta(hours=2)
    # after window expires, record fires again
    assert tracker.record(_run(), now=t1) is True


def test_different_jobs_tracked_independently(tracker):
    now = datetime(2024, 1, 1, 12, 0, 0)
    for _ in range(4):
        tracker.record(_run("job_a"), now=now)
    assert tracker.record(_run("job_b"), now=now) is True


def test_reset_clears_record(tracker):
    now = datetime(2024, 1, 1, 12, 0, 0)
    for _ in range(4):
        tracker.record(_run(), now=now)
    tracker.reset("backup")
    assert tracker.get("backup") is None
    assert tracker.record(_run(), now=now) is True


def test_active_anomalies_returns_current(tracker):
    now = datetime(2024, 1, 1, 12, 0, 0)
    tracker.record(_run("job_a"), now=now)
    tracker.record(_run("job_b"), now=now)
    names = {r.job_name for r in tracker.active_anomalies()}
    assert names == {"job_a", "job_b"}
