"""Tests for cronwatch.runlog and cronwatch.runlog_reporter."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwatch.runlog import RunLog, RunLogEntry, entry_from_run
from cronwatch.runlog_reporter import format_runlog_table, format_runlog_summary
from cronwatch.tracker import JobRun, JobStatus


def _utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2024, 1, 15, hour, minute, tzinfo=timezone.utc)


def _make_entry(
    job_name="backup",
    status="success",
    duration=30.0,
    exit_code=0,
    note="",
) -> RunLogEntry:
    return RunLogEntry(
        job_name=job_name,
        status=status,
        started_at=_utc(10),
        finished_at=_utc(10, 1),
        duration_seconds=duration,
        exit_code=exit_code,
        note=note,
    )


@pytest.fixture
def log_path(tmp_path) -> Path:
    return tmp_path / "runlog.jsonl"


@pytest.fixture
def log(log_path) -> RunLog:
    return RunLog(log_path)


# --- RunLogEntry serialisation ---

def test_to_dict_roundtrip():
    e = _make_entry(note="ok")
    d = e.to_dict()
    restored = RunLogEntry.from_dict(d)
    assert restored.job_name == e.job_name
    assert restored.status == e.status
    assert restored.duration_seconds == e.duration_seconds
    assert restored.note == e.note


def test_to_dict_none_datetimes():
    e = RunLogEntry("j", "success", None, None, None, None)
    d = e.to_dict()
    assert d["started_at"] is None
    assert d["finished_at"] is None


# --- entry_from_run ---

def test_entry_from_run_success():
    run = JobRun(job_name="sync", started_at=_utc(9))
    run.status = JobStatus.SUCCESS
    run.finished_at = _utc(9, 2)
    run.exit_code = 0
    e = entry_from_run(run, note="auto")
    assert e.job_name == "sync"
    assert e.status == "success"
    assert e.duration_seconds == pytest.approx(120.0)
    assert e.note == "auto"


def test_entry_from_run_no_finish():
    run = JobRun(job_name="sync", started_at=_utc(9))
    run.status = JobStatus.FAILURE
    run.finished_at = None
    e = entry_from_run(run)
    assert e.duration_seconds is None


# --- RunLog persistence ---

def test_load_returns_empty_when_no_file(log):
    assert log.load() == []


def test_append_and_load_roundtrip(log):
    e = _make_entry()
    log.append(e)
    loaded = log.load()
    assert len(loaded) == 1
    assert loaded[0].job_name == "backup"


def test_append_multiple_entries(log):
    for name in ["a", "b", "c"]:
        log.append(_make_entry(job_name=name))
    assert len(log.load()) == 3


def test_load_filters_by_job_name(log):
    log.append(_make_entry(job_name="alpha"))
    log.append(_make_entry(job_name="beta"))
    result = log.load(job_name="alpha")
    assert len(result) == 1
    assert result[0].job_name == "alpha"


def test_clear_removes_file(log):
    log.append(_make_entry())
    log.clear()
    assert not Path(log._path).exists()


# --- Reporter ---

def test_format_runlog_table_empty():
    assert "No run log entries" in format_runlog_table([])


def test_format_runlog_table_contains_job_name():
    table = format_runlog_table([_make_entry(job_name="myjob")])
    assert "myjob" in table


def test_format_runlog_table_contains_status():
    table = format_runlog_table([_make_entry(status="failure")])
    assert "failure" in table


def test_format_runlog_summary_counts():
    entries = [
        _make_entry(status="success"),
        _make_entry(status="failure"),
        _make_entry(status="success"),
    ]
    summary = format_runlog_summary(entries)
    assert "3" in summary
    assert "2" in summary  # successes
    assert "1" in summary  # failures


def test_format_runlog_summary_empty():
    assert "No entries" in format_runlog_summary([])
