"""Tests for cronwatch.sampling."""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import List

import pytest

from cronwatch.tracker import JobRun, JobStatus
from cronwatch.sampling import (
    SamplingConfig,
    SampleResult,
    sample_runs,
    filter_by_sample,
)


def _utc(hour: int = 0, minute: int = 0) -> datetime:
    return datetime(2024, 1, 1, hour, minute, tzinfo=timezone.utc)


def _run(name: str = "job", status: JobStatus = JobStatus.SUCCESS) -> JobRun:
    r = JobRun(job_name=name)
    r.start_time = _utc()
    r.end_time = _utc(0, 5)
    r.status = status
    return r


@pytest.fixture()
def runs() -> List[JobRun]:
    return [_run(f"job_{i}") for i in range(20)]


# ---------------------------------------------------------------------------
# SamplingConfig validation
# ---------------------------------------------------------------------------

def test_invalid_rate_raises():
    with pytest.raises(ValueError, match="rate"):
        SamplingConfig(rate=1.5)


def test_negative_min_samples_raises():
    with pytest.raises(ValueError, match="min_samples"):
        SamplingConfig(min_samples=-1)


# ---------------------------------------------------------------------------
# sample_runs — full rate
# ---------------------------------------------------------------------------

def test_full_rate_returns_all(runs):
    cfg = SamplingConfig(rate=1.0)
    result = sample_runs(runs, cfg)
    assert result.kept == len(runs)
    assert result.dropped == 0
    assert result.total == len(runs)


def test_empty_input_returns_empty():
    cfg = SamplingConfig(rate=0.5)
    result = sample_runs([], cfg)
    assert result.sampled == []
    assert result.total == 0
    assert result.effective_rate == 0.0


# ---------------------------------------------------------------------------
# sample_runs — partial rate
# ---------------------------------------------------------------------------

def test_partial_rate_reduces_count(runs):
    cfg = SamplingConfig(rate=0.3, seed=42)
    result = sample_runs(runs, cfg)
    assert result.kept < len(runs)
    assert result.dropped == len(runs) - result.kept


def test_seed_produces_deterministic_output(runs):
    cfg = SamplingConfig(rate=0.5, seed=99)
    r1 = sample_runs(runs, cfg)
    r2 = sample_runs(runs, cfg)
    assert [r.job_name for r in r1.sampled] == [r.job_name for r in r2.sampled]


def test_effective_rate_matches_fraction(runs):
    cfg = SamplingConfig(rate=1.0)
    result = sample_runs(runs, cfg)
    assert result.effective_rate == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# min_samples floor
# ---------------------------------------------------------------------------

def test_min_samples_floor_respected(runs):
    cfg = SamplingConfig(rate=0.0, min_samples=5, seed=0)
    result = sample_runs(runs, cfg)
    assert result.kept >= 5


def test_min_samples_does_not_exceed_total():
    few = [_run() for _ in range(3)]
    cfg = SamplingConfig(rate=0.0, min_samples=10, seed=0)
    result = sample_runs(few, cfg)
    assert result.kept == 3


# ---------------------------------------------------------------------------
# filter_by_sample convenience wrapper
# ---------------------------------------------------------------------------

def test_filter_by_sample_returns_list(runs):
    result = filter_by_sample(runs, rate=1.0)
    assert isinstance(result, list)
    assert len(result) == len(runs)


def test_filter_by_sample_with_seed_is_deterministic(runs):
    a = filter_by_sample(runs, rate=0.5, seed=7)
    b = filter_by_sample(runs, rate=0.5, seed=7)
    assert [r.job_name for r in a] == [r.job_name for r in b]
