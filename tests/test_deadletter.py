"""Tests for cronwatch.deadletter and cronwatch.deadletter_reporter."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwatch.deadletter import DeadLetter, DeadLetterQueue
from cronwatch.deadletter_reporter import format_deadletter_table


@pytest.fixture()
def queue(tmp_path):
    return DeadLetterQueue(path=str(tmp_path / "dl.jsonl"))


# ---------------------------------------------------------------------------
# DeadLetterQueue
# ---------------------------------------------------------------------------

def test_push_returns_dead_letter(queue):
    dl = queue.push("backup", "Subject", "Body", error="timeout")
    assert isinstance(dl, DeadLetter)
    assert dl.job_name == "backup"
    assert dl.attempts == 1
    assert dl.last_error == "timeout"


def test_push_creates_file(queue, tmp_path):
    queue.push("backup", "S", "B")
    assert Path(queue._path).exists()


def test_load_returns_empty_when_no_file(queue):
    assert queue.load() == []


def test_load_roundtrip(queue):
    queue.push("job-a", "Sub", "Bod", error="err")
    queue.push("job-b", "Sub2", "Bod2")
    letters = queue.load()
    assert len(letters) == 2
    assert letters[0].job_name == "job-a"
    assert letters[1].job_name == "job-b"


def test_clear_removes_all(queue):
    queue.push("job-a", "S", "B")
    queue.push("job-b", "S", "B")
    removed = queue.clear()
    assert removed == 2
    assert queue.load() == []


def test_clear_noop_when_empty(queue):
    assert queue.clear() == 0


def test_retry_all_success(queue):
    queue.push("job-a", "Sub", "Body")
    queue.push("job-b", "Sub", "Body")

    result = queue.retry_all(lambda s, b: True)

    assert result == {"replayed": 2, "failed": 0}
    assert queue.load() == []


def test_retry_all_partial_failure(queue):
    queue.push("job-a", "Sub", "Body")
    queue.push("job-b", "Sub", "Body")

    calls = []

    def dispatch(s, b):
        calls.append(s)
        return len(calls) == 1  # only first succeeds

    result = queue.retry_all(dispatch)
    assert result["replayed"] == 1
    assert result["failed"] == 1
    # Failed letter should still be in queue
    remaining = queue.load()
    assert len(remaining) == 1
    assert remaining[0].attempts == 2


def test_retry_all_empty_queue(queue):
    result = queue.retry_all(lambda s, b: True)
    assert result == {"replayed": 0, "failed": 0}


def test_retry_all_dispatch_raises(queue):
    queue.push("job-a", "Sub", "Body")

    def boom(s, b):
        raise RuntimeError("SMTP down")

    result = queue.retry_all(boom)
    assert result["failed"] == 1
    letters = queue.load()
    assert "SMTP down" in letters[0].last_error


# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------

def _make_dl(job="backup", attempts=1, error=None):
    from datetime import datetime, timezone
    return DeadLetter(
        job_name=job,
        subject="Alert",
        body="Body",
        queued_at=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
        attempts=attempts,
        last_error=error,
    )


def test_empty_returns_message():
    assert format_deadletter_table([]) == "Dead-letter queue is empty."


def test_table_contains_job_name():
    out = format_deadletter_table([_make_dl("nightly-backup")])
    assert "nightly-backup" in out


def test_table_contains_attempt_count():
    out = format_deadletter_table([_make_dl(attempts=3)])
    assert "3" in out


def test_table_contains_error():
    out = format_deadletter_table([_make_dl(error="connection refused")])
    assert "connection refused" in out


def test_table_footer_shows_count():
    letters = [_make_dl("a"), _make_dl("b")]
    out = format_deadletter_table(letters)
    assert "2 item(s)" in out
