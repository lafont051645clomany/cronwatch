"""Tests for cronwatch.throttle_reporter."""
from datetime import datetime, timezone

import pytest

from cronwatch.throttle import ThrottleConfig, Throttler
from cronwatch.throttle_reporter import format_throttle_table

T0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def throttler() -> Throttler:
    return Throttler(ThrottleConfig(window_seconds=60, max_alerts=3))


def test_empty_job_list_returns_message(throttler: Throttler) -> None:
    result = format_throttle_table(throttler, [], at=T0)
    assert result == "No jobs to display."


def test_table_contains_job_name(throttler: Throttler) -> None:
    result = format_throttle_table(throttler, ["backup"], at=T0)
    assert "backup" in result


def test_table_shows_zero_count_initially(throttler: Throttler) -> None:
    result = format_throttle_table(throttler, ["backup"], at=T0)
    assert "0" in result


def test_table_shows_allowed_yes(throttler: Throttler) -> None:
    result = format_throttle_table(throttler, ["backup"], at=T0)
    assert "yes" in result


def test_table_shows_no_when_blocked(throttler: Throttler) -> None:
    for _ in range(3):
        throttler.record("backup", at=T0)
    result = format_throttle_table(throttler, ["backup"], at=T0)
    assert "NO" in result


def test_table_sorted_by_job_name(throttler: Throttler) -> None:
    result = format_throttle_table(throttler, ["zzz", "aaa"], at=T0)
    assert result.index("aaa") < result.index("zzz")
