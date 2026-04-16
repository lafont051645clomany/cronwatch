"""Tests for cronwatch.baseline."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

import pytest

from cronwatch.baseline import BaselineStats, BaselineStore, compute_baseline
from cronwatch.tracker import JobRun, JobStatus


def _make_run(
    job_name: str,
    status: JobStatus = JobStatus.SUCCESS,
    duration: Optional[float] = 10.0,
) -> JobRun:
    now = datetime.now(timezone.utc)
    run = JobRun(job_name=job_name, started_at=now)
    run.status = status
    if duration is not None:
        from datetime import timedelta
        run.finished_at = now + timedelta(seconds=duration)
    return run


# ---------------------------------------------------------------------------
# BaselineStats.is_anomalous
# ---------------------------------------------------------------------------

def test_is_anomalous_too_few_samples():
    stats = BaselineStats(job_name="j", sample_count=1, mean_seconds=10.0, stddev_seconds=2.0)
    assert stats.is_anomalous(999.0) is False


def test_is_anomalous_zero_stddev():
    stats = BaselineStats(job_name="j", sample_count=5, mean_seconds=10.0, stddev_seconds=0.0)
    assert stats.is_anomalous(999.0) is False


def test_is_anomalous_within_threshold():
    stats = BaselineStats(job_name="j", sample_count=10, mean_seconds=10.0, stddev_seconds=2.0)
    assert stats.is_anomalous(11.0) is False  # z = 0.5


def test_is_anomalous_exceeds_threshold():
    stats = BaselineStats(job_name="j", sample_count=10, mean_seconds=10.0, stddev_seconds=2.0)
    assert stats.is_anomalous(20.0) is True  # z = 5.0


# ---------------------------------------------------------------------------
# compute_baseline
# ---------------------------------------------------------------------------

def test_compute_baseline_empty_runs():
    stats = compute_baseline("nojob", [])
    assert stats.sample_count == 0
    assert stats.mean_seconds == 0.0


def test_compute_baseline_ignores_failed_runs():
    runs = [
        _make_run("job", JobStatus.FAILURE, 5.0),
        _make_run("job", JobStatus.SUCCESS, 10.0),
    ]
    stats = compute_baseline("job", runs)
    assert stats.sample_count == 1
    assert stats.mean_seconds == 10.0


def test_compute_baseline_ignores_other_jobs():
    runs = [_make_run("other", JobStatus.SUCCESS, 10.0)]
    stats = compute_baseline("job", runs)
    assert stats.sample_count == 0


def test_compute_baseline_mean_and_stddev():
    runs = [_make_run("job", duration=d) for d in [10.0, 20.0, 30.0]]
    stats = compute_baseline("job", runs)
    assert stats.sample_count == 3
    assert stats.mean_seconds == pytest.approx(20.0)
    assert stats.stddev_seconds == pytest.approx((200 / 3) ** 0.5, rel=1e-3)


# ---------------------------------------------------------------------------
# BaselineStore
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    return BaselineStore(str(tmp_path / "baselines.json"))


def test_store_get_missing_returns_none(store):
    assert store.get("unknown") is None


def test_store_update_and_get(store):
    stats = BaselineStats(job_name="j", sample_count=5, mean_seconds=15.0, stddev_seconds=3.0)
    store.update(stats)
    result = store.get("j")
    assert result is not None
    assert result.mean_seconds == 15.0


def test_store_save_and_reload(tmp_path):
    path = str(tmp_path / "baselines.json")
    s1 = BaselineStore(path)
    s1.update(BaselineStats(job_name="j", sample_count=4, mean_seconds=8.0, stddev_seconds=1.5))
    s1.save()

    s2 = BaselineStore(path)
    result = s2.get("j")
    assert result is not None
    assert result.sample_count == 4
    assert result.stddev_seconds == 1.5


def test_store_all_returns_all_entries(store):
    store.update(BaselineStats(job_name="a", sample_count=1))
    store.update(BaselineStats(job_name="b", sample_count=2))
    assert set(store.all().keys()) == {"a", "b"}
