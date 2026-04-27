"""Tests for cronwatch.sla_reporter."""
from __future__ import annotations

from datetime import datetime, timezone

from cronwatch.sla import SLAViolation
from cronwatch.sla_reporter import format_sla_table


def _v(job_name: str = "backup", reason: str = "rate too low") -> SLAViolation:
    return SLAViolation(
        job_name=job_name,
        reason=reason,
        measured_at=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_empty_returns_no_violations_message():
    out = format_sla_table([])
    assert "No SLA violations" in out


def test_table_contains_job_name():
    out = format_sla_table([_v(job_name="nightly_sync")])
    assert "nightly_sync" in out


def test_table_contains_reason():
    out = format_sla_table([_v(reason="success rate 50.0% is below minimum 90.0%")])
    assert "50.0%" in out


def test_table_contains_timestamp():
    out = format_sla_table([_v()])
    assert "2024-06-01" in out
    assert "12:00:00" in out


def test_table_violation_count_in_footer():
    violations = [_v(job_name=f"job_{i}") for i in range(3)]
    out = format_sla_table(violations)
    assert "3 violation(s)" in out


def test_table_has_header_row():
    out = format_sla_table([_v()])
    assert "Job" in out
    assert "Reason" in out
    assert "Measured At" in out
