"""Tests for cronwatch.history — HistoryStore persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwatch.history import HistoryStore, _run_from_dict, _run_to_dict
from cronwatch.tracker import JobRun, JobStatus


@pytest.fixture()
def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(path=tmp_path / "history.json")


def _make_run(name: str = "backup", status: JobStatus = JobStatus.SUCCESS) -> JobRun:
    run = JobRun(job_name=name, started_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc))
    run.finished_at = datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
    run.status = status
    run.exit_code = 0 if status == JobStatus.SUCCESS else 1
    return run


def test_load_returns_empty_when_no_file(store: HistoryStore) -> None:
    assert store.load() == []


def test_save_and_load_roundtrip(store: HistoryStore) -> None:
    run = _make_run()
    store.save([run])
    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].job_name == "backup"
    assert loaded[0].status == JobStatus.SUCCESS
    assert loaded[0].exit_code == 0


def test_append_adds_to_existing(store: HistoryStore) -> None:
    store.append(_make_run("job_a"))
    store.append(_make_run("job_b"))
    runs = store.load()
    assert len(runs) == 2
    assert {r.job_name for r in runs} == {"job_a", "job_b"}


def test_runs_for_job_filters_correctly(store: HistoryStore) -> None:
    store.append(_make_run("alpha"))
    store.append(_make_run("beta"))
    store.append(_make_run("alpha"))
    result = store.runs_for_job("alpha")
    assert len(result) == 2
    assert all(r.job_name == "alpha" for r in result)


def test_clear_all(store: HistoryStore) -> None:
    store.append(_make_run())
    store.clear()
    assert store.load() == []


def test_clear_specific_job(store: HistoryStore) -> None:
    store.append(_make_run("keep"))
    store.append(_make_run("remove"))
    store.clear(job_name="remove")
    remaining = store.load()
    assert len(remaining) == 1
    assert remaining[0].job_name == "keep"


def test_run_to_dict_and_back(store: HistoryStore) -> None:
    run = _make_run(status=JobStatus.FAILURE)
    d = _run_to_dict(run)
    restored = _run_from_dict(d)
    assert restored.job_name == run.job_name
    assert restored.status == JobStatus.FAILURE
    assert restored.started_at == run.started_at
    assert restored.finished_at == run.finished_at


def test_finished_at_none_handled(store: HistoryStore) -> None:
    run = JobRun(job_name="active", started_at=datetime(2024, 6, 1, tzinfo=timezone.utc))
    run.status = JobStatus.UNKNOWN
    store.append(run)
    loaded = store.load()
    assert loaded[0].finished_at is None
