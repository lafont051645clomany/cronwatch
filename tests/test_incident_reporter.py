"""Tests for cronwatch.incident_reporter."""
from __future__ import annotations

from datetime import datetime, timezone

from cronwatch.incident import Incident
from cronwatch.incident_reporter import (
    format_incident_summary,
    format_incident_table,
)


def _utc(hour: int) -> datetime:
    return datetime(2024, 1, 15, hour, 0, tzinfo=timezone.utc)


def _open_incident(name: str = "backup") -> Incident:
    return Incident(job_name=name, started_at=_utc(10), failure_count=3)


def _resolved_incident(name: str = "sync") -> Incident:
    inc = Incident(job_name=name, started_at=_utc(8), failure_count=1)
    inc.resolved_at = _utc(9)
    return inc


def test_empty_returns_message():
    assert format_incident_table([]) == "No incidents recorded."


def test_table_contains_job_name():
    table = format_incident_table([_open_incident()])
    assert "backup" in table


def test_table_contains_failure_count():
    table = format_incident_table([_open_incident()])
    assert "3" in table


def test_table_shows_open_status():
    table = format_incident_table([_open_incident()])
    assert "OPEN" in table


def test_table_shows_resolved_status():
    table = format_incident_table([_resolved_incident()])
    assert "RESOLVED" in table


def test_table_contains_header_fields():
    table = format_incident_table([_open_incident()])
    assert "Job" in table
    assert "Failures" in table
    assert "Status" in table


def test_table_multiple_rows():
    incidents = [_open_incident("job_a"), _resolved_incident("job_b")]
    table = format_incident_table(incidents)
    assert "job_a" in table
    assert "job_b" in table


def test_summary_counts():
    incidents = [_open_incident(), _resolved_incident()]
    summary = format_incident_summary(incidents)
    assert "2 total" in summary
    assert "1 open" in summary
    assert "1 resolved" in summary


def test_summary_all_open():
    incidents = [_open_incident("a"), _open_incident("b")]
    summary = format_incident_summary(incidents)
    assert "2 open" in summary
    assert "0 resolved" in summary
