"""Tests for cronwatch.watchdog."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from cronwatch.tracker import JobRun, JobStatus
from cronwatch.watchdog import Watchdog, WatchdogConfig, WatchdogViolation

_BASE = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _run(
    job_name: str,
    finished_offset: float | None = 0.0,
    status: JobStatus = JobStatus.SUCCESS,
) -> JobRun:
    started = _BASE
    finished = (
        datetime.fromtimestamp(_BASE.timestamp() + finished_offset, tz=timezone.utc)
        if finished_offset is not None
        else None
    )
    return JobRun(
        job_name=job_name,
        started_at=started,
        finished_at=finished,
        status=status,
        exit_code=0,
        duration_seconds=finished_offset,
    )


@pytest.fixture()
def cfg() -> WatchdogConfig:
    return WatchdogConfig(job_name="backup", max_silence_seconds=3600)


@pytest.fixture()
def watchdog(cfg: WatchdogConfig) -> Watchdog:
    return Watchdog([cfg])


def test_no_violation_when_run_is_recent(watchdog: Watchdog) -> None:
    # finished 60s before "now" — well within 3600s threshold
    now = datetime.fromtimestamp(_BASE.timestamp() + 60, tz=timezone.utc)
    run = _run("backup", finished_offset=0.0)
    with patch("cronwatch.watchdog._now", return_value=now):
        violations = watchdog.check([run])
    assert violations == []


def test_violation_when_run_is_stale(watchdog: Watchdog) -> None:
    # "now" is 7200s after the run finished — exceeds 3600s threshold
    now = datetime.fromtimestamp(_BASE.timestamp() + 7200, tz=timezone.utc)
    run = _run("backup", finished_offset=0.0)
    with patch("cronwatch.watchdog._now", return_value=now):
        violations = watchdog.check([run])
    assert len(violations) == 1
    assert violations[0].job_name == "backup"
    assert violations[0].silence_seconds == pytest.approx(7200, abs=1)


def test_violation_when_job_never_run(watchdog: Watchdog) -> None:
    with patch("cronwatch.watchdog._now", return_value=_BASE):
        violations = watchdog.check([])
    assert len(violations) == 1
    assert violations[0].last_seen is None


def test_disabled_config_skipped() -> None:
    cfg = WatchdogConfig(job_name="nightly", max_silence_seconds=60, enabled=False)
    wd = Watchdog([cfg])
    with patch("cronwatch.watchdog._now", return_value=_BASE):
        violations = wd.check([])
    assert violations == []


def test_uses_most_recent_run(watchdog: Watchdog) -> None:
    # Two runs for same job; the later one is recent enough
    now = datetime.fromtimestamp(_BASE.timestamp() + 100, tz=timezone.utc)
    old_run = _run("backup", finished_offset=0.0)  # finished at _BASE
    # newer run finished 90s after _BASE — still within 3600s
    new_run = _run("backup", finished_offset=90.0)
    with patch("cronwatch.watchdog._now", return_value=now):
        violations = watchdog.check([old_run, new_run])
    assert violations == []


def test_violation_message_never_seen() -> None:
    v = WatchdogViolation(
        job_name="sync",
        last_seen=None,
        silence_seconds=9999,
        threshold_seconds=3600,
    )
    assert "never" in v.message
    assert "sync" in v.message


def test_violation_message_with_last_seen() -> None:
    v = WatchdogViolation(
        job_name="sync",
        last_seen=_BASE,
        silence_seconds=7200.0,
        threshold_seconds=3600,
    )
    assert "7200" in v.message or "7200.0" in v.message
    assert "sync" in v.message
