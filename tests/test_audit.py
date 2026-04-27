"""Tests for cronwatch.audit and cronwatch.audit_reporter."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwatch.audit import AuditEntry, AuditLog
from cronwatch.audit_reporter import format_audit_table, format_audit_summary


_UTC = timezone.utc


def _utc(year=2024, month=1, day=1, hour=0, minute=0, second=0) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=_UTC)


@pytest.fixture()
def log(tmp_path: Path) -> AuditLog:
    return AuditLog(tmp_path / "audit.ndjson")


def _entry(**kwargs) -> AuditEntry:
    defaults = dict(
        job_name="backup",
        event="alert_dispatched",
        status="ok",
        channel="email",
        detail="sent",
        timestamp=_utc(),
    )
    defaults.update(kwargs)
    return AuditEntry(**defaults)


# ── AuditEntry ────────────────────────────────────────────────────────────────

def test_to_dict_roundtrip():
    e = _entry()
    assert AuditEntry.from_dict(e.to_dict()) == e


def test_to_dict_contains_expected_keys():
    d = _entry().to_dict()
    for key in ("job_name", "event", "status", "channel", "detail", "timestamp"):
        assert key in d


# ── AuditLog ─────────────────────────────────────────────────────────────────

def test_load_returns_empty_when_no_file(log: AuditLog):
    assert log.load() == []


def test_record_and_load_roundtrip(log: AuditLog):
    e = _entry()
    log.record(e)
    loaded = log.load()
    assert len(loaded) == 1
    assert loaded[0].job_name == "backup"
    assert loaded[0].status == "ok"


def test_multiple_records_preserved_in_order(log: AuditLog):
    e1 = _entry(event="alert_dispatched", timestamp=_utc(hour=1))
    e2 = _entry(event="alert_suppressed", timestamp=_utc(hour=2))
    log.record(e1)
    log.record(e2)
    loaded = log.load()
    assert [e.event for e in loaded] == ["alert_dispatched", "alert_suppressed"]


def test_load_for_job_filters_by_name(log: AuditLog):
    log.record(_entry(job_name="backup"))
    log.record(_entry(job_name="cleanup"))
    result = log.load_for_job("backup")
    assert len(result) == 1
    assert result[0].job_name == "backup"


def test_load_for_job_case_insensitive(log: AuditLog):
    log.record(_entry(job_name="Backup"))
    result = log.load_for_job("backup")
    assert len(result) == 1


def test_clear_removes_file(log: AuditLog, tmp_path: Path):
    log.record(_entry())
    log.clear()
    assert not (tmp_path / "audit.ndjson").exists()


# ── audit_reporter ────────────────────────────────────────────────────────────

def test_format_audit_table_empty():
    assert "No audit entries" in format_audit_table([])


def test_format_audit_table_contains_job_name():
    table = format_audit_table([_entry(job_name="myjob")])
    assert "myjob" in table


def test_format_audit_table_contains_status():
    table = format_audit_table([_entry(status="error")])
    assert "error" in table


def test_format_audit_summary_empty():
    assert "empty" in format_audit_summary([])


def test_format_audit_summary_counts():
    entries = [
        _entry(status="ok"),
        _entry(status="ok"),
        _entry(status="error"),
    ]
    summary = format_audit_summary(entries)
    assert "3 total" in summary
    assert "ok: 2" in summary
    assert "error: 1" in summary
