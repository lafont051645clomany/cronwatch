"""Tests for cronwatch.window sliding-window statistics."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from cronwatch.tracker import JobRun, JobStatus
from cronwatch.window import WindowConfig, WindowStats, compute_window_stats, compute_all


def _utc(offset_minutes: int = 0) -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(
        minutes=offset_minutes
    )


def _run(
    name: str,
    status: JobStatus,
    started_offset: int,
    duration: float = 10.0,
) -> JobRun:
    start = _utc(started_offset)
    r = JobRun(job_name=name, run_id="x", started_at=start)
    r.status = status
    r.finished_at = start + timedelta(seconds=duration)
    return r


@pytest.fixture
def runs():
    return [
        _run("backup", JobStatus.SUCCESS, -30, duration=20.0),
        _run("backup", JobStatus.SUCCESS, -20, duration=40.0),
        _run("backup", JobStatus.FAILED, -10, duration=5.0),
        _run("sync", JobStatus.SUCCESS, -45, duration=60.0),
        _run("sync", JobStatus.FAILED, -5, duration=15.0),
    ]


@pytest.fixture
def cfg():
    return WindowConfig(size_minutes=60)


def test_compute_window_stats_counts_samples(runs, cfg):
    stats = compute_window_stats("backup", runs, cfg, now=_utc())
    assert stats.sample_count == 3


def test_compute_window_stats_counts_failures(runs, cfg):
    stats = compute_window_stats("backup", runs, cfg, now=_utc())
    assert stats.failure_count == 1


def test_compute_window_stats_failure_rate(runs, cfg):
    stats = compute_window_stats("backup", runs, cfg, now=_utc())
    assert abs(stats.failure_rate - 1 / 3) < 1e-9


def test_compute_window_stats_avg_duration(runs, cfg):
    stats = compute_window_stats("backup", runs, cfg, now=_utc())
    assert abs(stats.avg_duration - (20.0 + 40.0 + 5.0) / 3) < 1e-9


def test_compute_window_stats_p95(runs, cfg):
    stats = compute_window_stats("backup", runs, cfg, now=_utc())
    assert stats.p95_duration is not None


def test_compute_window_excludes_old_runs(runs, cfg):
    # Only runs within last 15 minutes
    narrow_cfg = WindowConfig(size_minutes=15)
    stats = compute_window_stats("backup", runs, narrow_cfg, now=_utc())
    assert stats.sample_count == 1
    assert stats.failure_count == 1


def test_compute_window_empty_returns_zero_rate(cfg):
    stats = compute_window_stats("missing", [], cfg, now=_utc())
    assert stats.sample_count == 0
    assert stats.failure_rate == 0.0
    assert stats.avg_duration is None
    assert stats.p95_duration is None


def test_compute_all_returns_one_entry_per_job(runs, cfg):
    all_stats = compute_all(runs, cfg, now=_utc())
    names = {s.job_name for s in all_stats}
    assert names == {"backup", "sync"}


def test_has_enough_samples_true_when_samples_present(runs, cfg):
    stats = compute_window_stats("backup", runs, cfg, now=_utc())
    assert stats.has_enough_samples is True


def test_has_enough_samples_false_when_no_samples(cfg):
    stats = compute_window_stats("ghost", [], cfg, now=_utc())
    assert stats.has_enough_samples is False
