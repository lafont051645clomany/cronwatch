"""Tests for cronwatch.checkpoint and cronwatch.checkpoint_reporter."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cronwatch.checkpoint import CheckpointStore
from cronwatch.checkpoint_reporter import format_checkpoint_table


@pytest.fixture
def store(tmp_path: Path) -> CheckpointStore:
    return CheckpointStore(tmp_path / "checkpoints.json")


def _utc(**kwargs) -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(**kwargs)


def test_get_returns_none_when_empty(store: CheckpointStore) -> None:
    assert store.get("backup") is None


def test_set_and_get_roundtrip(store: CheckpointStore) -> None:
    ts = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    store.set("backup", ts)
    result = store.get("backup")
    assert result is not None
    assert result.year == 2024 and result.month == 6 and result.day == 1


def test_set_defaults_to_now(store: CheckpointStore) -> None:
    before = datetime.now(tz=timezone.utc)
    store.set("cleanup")
    after = datetime.now(tz=timezone.utc)
    result = store.get("cleanup")
    assert result is not None
    assert before <= result <= after


def test_persists_to_disk(tmp_path: Path) -> None:
    path = tmp_path / "cp.json"
    s1 = CheckpointStore(path)
    ts = datetime(2024, 1, 15, 8, 30, 0, tzinfo=timezone.utc)
    s1.set("nightly", ts)
    s2 = CheckpointStore(path)
    assert s2.get("nightly") is not None


def test_remove_deletes_entry(store: CheckpointStore) -> None:
    store.set("job_a")
    store.remove("job_a")
    assert store.get("job_a") is None


def test_remove_noop_for_unknown(store: CheckpointStore) -> None:
    store.remove("ghost")  # should not raise


def test_all_returns_all_entries(store: CheckpointStore) -> None:
    store.set("a")
    store.set("b")
    result = store.all()
    assert set(result.keys()) == {"a", "b"}


def test_clear_removes_all(store: CheckpointStore) -> None:
    store.set("x")
    store.set("y")
    store.clear()
    assert store.all() == {}


# --- reporter ---

def test_format_empty_returns_message() -> None:
    assert "No checkpoints" in format_checkpoint_table({})


def test_format_table_contains_job_name() -> None:
    ts = datetime(2024, 3, 10, 9, 0, 0, tzinfo=timezone.utc)
    out = format_checkpoint_table({"my_job": ts})
    assert "my_job" in out


def test_format_table_contains_date() -> None:
    ts = datetime(2024, 3, 10, 9, 0, 0, tzinfo=timezone.utc)
    out = format_checkpoint_table({"my_job": ts})
    assert "2024-03-10" in out
