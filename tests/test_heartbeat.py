"""Tests for cronwatch.heartbeat."""
from datetime import datetime, timedelta, timezone

import pytest

from cronwatch.heartbeat import HeartbeatConfig, HeartbeatMonitor, HeartbeatViolation
from cronwatch.tracker import JobRun, JobStatus


def _utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2024, 1, 15, hour, minute, tzinfo=timezone.utc)


def _run(
    job_name: str,
    finished_at: datetime,
    status: JobStatus = JobStatus.SUCCESS,
) -> JobRun:
    return JobRun(
        job_name=job_name,
        started_at=finished_at - timedelta(seconds=10),
        finished_at=finished_at,
        status=status,
    )


@pytest.fixture
def monitor() -> HeartbeatMonitor:
    return HeartbeatMonitor(
        configs=[
            HeartbeatConfig("backup", max_silence=timedelta(hours=1)),
            HeartbeatConfig("cleanup", max_silence=timedelta(hours=6)),
        ]
    )


# ---------------------------------------------------------------------------
# record()
# ---------------------------------------------------------------------------

def test_record_updates_last_seen(monitor: HeartbeatMonitor) -> None:
    run = _run("backup", _utc(10))
    monitor.record(run)
    assert monitor._last_seen["backup"] == _utc(10)


def test_record_keeps_latest_timestamp(monitor: HeartbeatMonitor) -> None:
    monitor.record(_run("backup", _utc(9)))
    monitor.record(_run("backup", _utc(11)))
    monitor.record(_run("backup", _utc(10)))
    assert monitor._last_seen["backup"] == _utc(11)


def test_record_run_without_timestamps_is_ignored(monitor: HeartbeatMonitor) -> None:
    run = JobRun(job_name="backup", started_at=None, finished_at=None, status=JobStatus.FAILURE)
    monitor.record(run)
    assert "backup" not in monitor._last_seen


def test_record_uses_finished_at_over_started_at(monitor: HeartbeatMonitor) -> None:
    run = JobRun(
        job_name="backup",
        started_at=_utc(9),
        finished_at=_utc(10),
        status=JobStatus.SUCCESS,
    )
    monitor.record(run)
    assert monitor._last_seen["backup"] == _utc(10)


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------

def test_check_no_violations_when_recent(monitor: HeartbeatMonitor) -> None:
    monitor.record(_run("backup", _utc(10)))
    monitor.record(_run("cleanup", _utc(10)))
    violations = monitor.check(at=_utc(10, 30))
    assert violations == []


def test_check_violation_when_job_silent_too_long(monitor: HeartbeatMonitor) -> None:
    monitor.record(_run("backup", _utc(8)))
    monitor.record(_run("cleanup", _utc(8)))
    violations = monitor.check(at=_utc(10))
    names = [v.job_name for v in violations]
    assert "backup" in names   # 2h silence > 1h threshold
    assert "cleanup" not in names  # 2h silence < 6h threshold


def test_check_violation_when_job_never_run(monitor: HeartbeatMonitor) -> None:
    violations = monitor.check(at=_utc(12))
    names = [v.job_name for v in violations]
    assert "backup" in names
    assert "cleanup" in names


def test_check_never_run_violation_has_none_last_seen(monitor: HeartbeatMonitor) -> None:
    violations = monitor.check(at=_utc(12))
    v = next(x for x in violations if x.job_name == "backup")
    assert v.last_seen is None
    assert v.silence_duration is None


def test_violation_message_never_run() -> None:
    v = HeartbeatViolation(
        job_name="backup",
        last_seen=None,
        silence_duration=None,
        threshold=timedelta(hours=1),
    )
    msg = v.message()
    assert "never" in msg
    assert "backup" in msg


def test_violation_message_with_silence() -> None:
    v = HeartbeatViolation(
        job_name="cleanup",
        last_seen=_utc(8),
        silence_duration=timedelta(hours=3),
        threshold=timedelta(hours=2),
    )
    msg = v.message()
    assert "cleanup" in msg
    assert "10800s" in msg  # 3 * 3600
    assert "7200s" in msg   # threshold
