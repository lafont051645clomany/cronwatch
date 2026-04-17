"""Tests for cronwatch.escalation_reporter."""
from datetime import datetime
from cronwatch.escalation import EscalationState
from cronwatch.escalation_reporter import format_escalation_table


def _state(job, fails, escalated=None, resolved=None):
    s = EscalationState(job_name=job, consecutive_failures=fails)
    s.escalated_at = escalated
    s.resolved_at = resolved
    return s


def test_empty_returns_message():
    assert format_escalation_table([]) == "No escalated jobs."


def test_table_contains_job_name():
    s = _state("backup", 3, datetime(2024, 1, 1, 8, 0, 0))
    out = format_escalation_table([s])
    assert "backup" in out


def test_table_contains_failure_count():
    s = _state("sync", 5, datetime(2024, 1, 2, 9, 0, 0))
    out = format_escalation_table([s])
    assert "5" in out


def test_table_contains_escalated_at():
    t = datetime(2024, 3, 10, 14, 30, 0)
    s = _state("report", 3, escalated=t)
    out = format_escalation_table([s])
    assert "2024-03-10 14:30:00" in out


def test_table_dash_when_not_resolved():
    s = _state("cleanup", 4, datetime(2024, 1, 5, 6, 0, 0))
    out = format_escalation_table([s])
    lines = out.splitlines()
    data_line = lines[-1]
    assert "-" in data_line


def test_table_multiple_rows():
    states = [
        _state("job_a", 3, datetime(2024, 1, 1)),
        _state("job_b", 7, datetime(2024, 1, 2)),
    ]
    out = format_escalation_table(states)
    assert "job_a" in out
    assert "job_b" in out
