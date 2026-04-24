"""Tests for cronwatch.watchdog_reporter."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronwatch.watchdog import WatchdogViolation
from cronwatch.watchdog_reporter import format_watchdog_table

_BASE = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _violation(
    job_name: str = "backup",
    last_seen: datetime | None = _BASE,
    silence: float = 7200.0,
    threshold: float = 3600.0,
) -> WatchdogViolation:
    return WatchdogViolation(
        job_name=job_name,
        last_seen=last_seen,
        silence_seconds=silence,
        threshold_seconds=threshold,
    )


def test_empty_returns_no_issues_message() -> None:
    result = format_watchdog_table([])
    assert "No watchdog violations" in result


def test_table_contains_job_name() -> None:
    result = format_watchdog_table([_violation(job_name="nightly_backup")])
    assert "nightly_backup" in result


def test_table_contains_silence_value() -> None:
    result = format_watchdog_table([_violation(silence=7200.0)])
    assert "7200" in result


def test_table_contains_threshold_value() -> None:
    result = format_watchdog_table([_violation(threshold=3600.0)])
    assert "3600" in result


def test_table_shows_never_for_unseen_job() -> None:
    result = format_watchdog_table([_violation(last_seen=None)])
    assert "never" in result


def test_table_contains_header() -> None:
    result = format_watchdog_table([_violation()])
    assert "Job" in result
    assert "Last Seen" in result


def test_multiple_violations_sorted_by_name() -> None:
    v1 = _violation(job_name="zzz_job")
    v2 = _violation(job_name="aaa_job")
    result = format_watchdog_table([v1, v2])
    lines = result.splitlines()
    job_lines = [l for l in lines if "job" in l]
    assert job_lines[0].strip().startswith("aaa_job")
    assert job_lines[1].strip().startswith("zzz_job")
