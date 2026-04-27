"""Tests for cronwatch.incident."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronwatch.incident import Incident, IncidentTracker
from cronwatch.tracker import JobRun, JobStatus


def _utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2024, 1, 15, hour, minute, tzinfo=timezone.utc)


def _run(
    name: str,
    status: JobStatus,
    started: datetime | None = None,
    finished: datetime | None = None,
    run_id: str | None = None,
) -> JobRun:
    r = JobRun(job_name=name)
    r.status = status
    r.started_at = started
    r.finished_at = finished
    r.run_id = run_id
    return r


@pytest.fixture
def tracker() -> IncidentTracker:
    return IncidentTracker()


def test_failure_opens_incident(tracker):
    run = _run("backup", JobStatus.FAILURE, started=_utc(10), run_id="r1")
    inc = tracker.record(run)
    assert inc is not None
    assert inc.is_open
    assert inc.job_name == "backup"
    assert inc.failure_count == 1
    assert "r1" in inc.run_ids


def test_consecutive_failures_increment_count(tracker):
    tracker.record(_run("backup", JobStatus.FAILURE, started=_utc(10), run_id="r1"))
    inc = tracker.record(_run("backup", JobStatus.FAILURE, started=_utc(11), run_id="r2"))
    assert inc.failure_count == 2
    assert len(inc.run_ids) == 2


def test_success_resolves_open_incident(tracker):
    tracker.record(_run("backup", JobStatus.FAILURE, started=_utc(10)))
    inc = tracker.record(
        _run("backup", JobStatus.SUCCESS, finished=_utc(11))
    )
    assert inc is not None
    assert not inc.is_open
    assert inc.resolved_at == _utc(11)


def test_success_with_no_open_incident_returns_none(tracker):
    result = tracker.record(_run("backup", JobStatus.SUCCESS))
    assert result is None


def test_get_open_returns_incident(tracker):
    tracker.record(_run("backup", JobStatus.FAILURE, started=_utc(10)))
    assert tracker.get_open("backup") is not None
    assert tracker.get_open("other") is None


def test_open_incidents_list(tracker):
    tracker.record(_run("job_a", JobStatus.FAILURE, started=_utc(10)))
    tracker.record(_run("job_b", JobStatus.FAILURE, started=_utc(10)))
    tracker.record(_run("job_a", JobStatus.SUCCESS, finished=_utc(11)))
    assert len(tracker.open_incidents()) == 1
    assert tracker.open_incidents()[0].job_name == "job_b"


def test_closed_incidents_list(tracker):
    tracker.record(_run("job_a", JobStatus.FAILURE, started=_utc(10)))
    tracker.record(_run("job_a", JobStatus.SUCCESS, finished=_utc(11)))
    assert len(tracker.closed_incidents()) == 1


def test_duration_seconds_none_when_open(tracker):
    tracker.record(_run("backup", JobStatus.FAILURE, started=_utc(10)))
    inc = tracker.get_open("backup")
    assert inc.duration_seconds is None


def test_duration_seconds_when_resolved(tracker):
    tracker.record(_run("backup", JobStatus.FAILURE, started=_utc(10)))
    inc = tracker.record(_run("backup", JobStatus.SUCCESS, finished=_utc(12)))
    assert inc.duration_seconds == 7200.0


def test_incident_message_open(tracker):
    tracker.record(_run("backup", JobStatus.FAILURE, started=_utc(10)))
    inc = tracker.get_open("backup")
    msg = inc.message()
    assert "OPEN" in msg
    assert "backup" in msg


def test_incident_message_resolved(tracker):
    tracker.record(_run("backup", JobStatus.FAILURE, started=_utc(10)))
    inc = tracker.record(_run("backup", JobStatus.SUCCESS, finished=_utc(11)))
    assert "RESOLVED" in inc.message()
