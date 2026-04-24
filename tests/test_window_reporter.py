"""Tests for cronwatch.window_reporter table formatting."""
from __future__ import annotations

import pytest

from cronwatch.window import WindowStats
from cronwatch.window_reporter import format_window_table


def _stat(
    name: str = "backup",
    samples: int = 5,
    failures: int = 1,
    avg: float = 30.0,
    p95: float = 55.0,
) -> WindowStats:
    return WindowStats(
        job_name=name,
        window_minutes=60,
        sample_count=samples,
        failure_count=failures,
        avg_duration=avg,
        p95_duration=p95,
        failure_rate=failures / samples if samples else 0.0,
    )


def test_empty_returns_no_data_message():
    result = format_window_table([], window_minutes=60)
    assert "No data" in result


def test_table_contains_job_name():
    result = format_window_table([_stat("backup")], window_minutes=60)
    assert "backup" in result


def test_table_contains_sample_count():
    result = format_window_table([_stat(samples=7)], window_minutes=60)
    assert "7" in result


def test_table_contains_failure_count():
    result = format_window_table([_stat(failures=2, samples=10)], window_minutes=60)
    assert "2" in result


def test_table_contains_avg_duration():
    result = format_window_table([_stat(avg=42.5)], window_minutes=60)
    assert "42.5" in result


def test_table_contains_p95_duration():
    result = format_window_table([_stat(p95=99.9)], window_minutes=60)
    assert "99.9" in result


def test_table_shows_window_size():
    result = format_window_table([_stat()], window_minutes=30)
    assert "30" in result


def test_table_none_duration_shows_dash():
    s = WindowStats(
        job_name="ghost",
        window_minutes=60,
        sample_count=1,
        failure_count=0,
        avg_duration=None,
        p95_duration=None,
        failure_rate=0.0,
    )
    result = format_window_table([s], window_minutes=60)
    assert "—" in result


def test_multiple_jobs_all_present():
    stats = [_stat("alpha"), _stat("beta"), _stat("gamma")]
    result = format_window_table(stats, window_minutes=60)
    assert "alpha" in result
    assert "beta" in result
    assert "gamma" in result
