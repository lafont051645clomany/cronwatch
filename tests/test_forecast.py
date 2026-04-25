"""Tests for cronwatch.forecast."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import pytest

from cronwatch.tracker import JobRun, JobStatus
from cronwatch.forecast import forecast, ForecastResult, _bucket_fail_rates


def _utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2024, 1, 1, hour, minute, tzinfo=timezone.utc)


def _run(
    job: str,
    status: JobStatus,
    hour: int,
    duration: float = 10.0,
) -> JobRun:
    started = _utc(hour)
    return JobRun(
        job_name=job,
        status=status,
        started_at=started,
        finished_at=_utc(hour, 0),
        duration_seconds=duration,
    )


def _make_runs(job: str, pattern: List[JobStatus]) -> List[JobRun]:
    """Create one run per hour following *pattern*."""
    return [_run(job, s, i % 24) for i, s in enumerate(pattern)]


# --- _bucket_fail_rates ---

def test_bucket_fail_rates_empty():
    assert _bucket_fail_rates([]) == []


def test_bucket_fail_rates_all_success():
    runs = _make_runs("job", [JobStatus.SUCCESS] * 6)
    rates = _bucket_fail_rates(runs, bucket_minutes=60)
    assert all(r == 0.0 for r in rates)


def test_bucket_fail_rates_all_failure():
    runs = _make_runs("job", [JobStatus.FAILED] * 6)
    rates = _bucket_fail_rates(runs, bucket_minutes=60)
    assert all(r == 1.0 for r in rates)


# --- forecast: insufficient samples ---

def test_forecast_insufficient_samples_returns_low_confidence():
    runs = _make_runs("job", [JobStatus.FAILED, JobStatus.SUCCESS, JobStatus.FAILED])
    result = forecast("job", runs)
    assert result.confidence == "low"
    assert result.slope_per_hour is None
    assert result.predicted_fail_rate_1h is None
    assert result.predicted_fail_rate_24h is None


def test_forecast_insufficient_samples_counts_correctly():
    runs = _make_runs("job", [JobStatus.FAILED] * 3)
    result = forecast("job", runs)
    assert result.samples == 3


# --- forecast: sufficient samples ---

def test_forecast_medium_confidence_with_enough_samples():
    runs = _make_runs("job", [JobStatus.SUCCESS] * 10)
    result = forecast("job", runs)
    assert result.confidence == "medium"
    assert result.slope_per_hour is not None


def test_forecast_high_confidence_with_many_samples():
    runs = _make_runs("job", [JobStatus.SUCCESS] * 20)
    result = forecast("job", runs)
    assert result.confidence == "high"


def test_forecast_flat_trend_not_degrading():
    runs = _make_runs("job", [JobStatus.SUCCESS] * 12)
    result = forecast("job", runs)
    assert not result.is_degrading


def test_forecast_current_fail_rate_all_failures():
    runs = _make_runs("job", [JobStatus.FAILED] * 10)
    result = forecast("job", runs)
    assert result.current_fail_rate == pytest.approx(1.0)


def test_forecast_filters_by_job_name():
    runs = _make_runs("job_a", [JobStatus.FAILED] * 8)
    runs += _make_runs("job_b", [JobStatus.SUCCESS] * 8)
    result = forecast("job_b", runs)
    assert result.current_fail_rate == pytest.approx(0.0)
    assert result.samples == 8


def test_forecast_predicted_rates_clamped_between_0_and_1():
    # All successes → slope near 0, predictions should stay in [0, 1]
    runs = _make_runs("job", [JobStatus.SUCCESS] * 10)
    result = forecast("job", runs)
    if result.predicted_fail_rate_1h is not None:
        assert 0.0 <= result.predicted_fail_rate_1h <= 1.0
    if result.predicted_fail_rate_24h is not None:
        assert 0.0 <= result.predicted_fail_rate_24h <= 1.0
