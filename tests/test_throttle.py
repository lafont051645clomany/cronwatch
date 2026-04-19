"""Tests for cronwatch.throttle."""
from datetime import datetime, timedelta, timezone

import pytest

from cronwatch.throttle import ThrottleConfig, Throttler

T0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def cfg() -> ThrottleConfig:
    return ThrottleConfig(window_seconds=60, max_alerts=3)


@pytest.fixture
def throttler(cfg: ThrottleConfig) -> Throttler:
    return Throttler(cfg)


def test_first_alert_allowed(throttler: Throttler) -> None:
    assert throttler.is_allowed("job_a", at=T0) is True


def test_record_increments_count(throttler: Throttler) -> None:
    throttler.record("job_a", at=T0)
    assert throttler.current_count("job_a", at=T0) == 1


def test_within_max_alerts_allowed(throttler: Throttler) -> None:
    for _ in range(2):
        throttler.record("job_a", at=T0)
    assert throttler.is_allowed("job_a", at=T0) is True


def test_exceeds_max_alerts_blocked(throttler: Throttler) -> None:
    for _ in range(3):
        throttler.record("job_a", at=T0)
    assert throttler.is_allowed("job_a", at=T0) is False


def test_old_records_evicted(throttler: Throttler) -> None:
    for _ in range(3):
        throttler.record("job_a", at=T0)
    future = T0 + timedelta(seconds=61)
    assert throttler.is_allowed("job_a", at=future) is True


def test_reset_clears_state(throttler: Throttler) -> None:
    for _ in range(3):
        throttler.record("job_a", at=T0)
    throttler.reset("job_a")
    assert throttler.is_allowed("job_a", at=T0) is True


def test_different_jobs_independent(throttler: Throttler) -> None:
    for _ in range(3):
        throttler.record("job_a", at=T0)
    assert throttler.is_allowed("job_b", at=T0) is True


def test_current_count_unknown_job_is_zero(throttler: Throttler) -> None:
    assert throttler.current_count("ghost", at=T0) == 0
