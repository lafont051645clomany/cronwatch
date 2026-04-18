"""Tests for cronwatch.runlock."""

import os
import time
from pathlib import Path

import pytest

from cronwatch.runlock import LockError, LockInfo, RunLock, _pid_alive


@pytest.fixture
def lock(tmp_path):
    return RunLock(lock_dir=tmp_path / "locks")


def test_acquire_returns_lock_info(lock):
    info = lock.acquire("backup")
    assert isinstance(info, LockInfo)
    assert info.job_name == "backup"
    assert info.pid == os.getpid()
    assert info.acquired_at <= time.time()


def test_acquire_creates_lock_file(lock, tmp_path):
    lock.acquire("backup")
    assert lock.is_locked("backup")


def test_release_removes_lock(lock):
    lock.acquire("backup")
    lock.release("backup")
    assert not lock.is_locked("backup")


def test_release_noop_when_not_locked(lock):
    lock.release("nonexistent")  # should not raise


def test_acquire_raises_if_already_locked(lock):
    lock.acquire("backup")
    with pytest.raises(LockError, match="already running"):
        lock.acquire("backup")


def test_stale_lock_is_replaced(lock, tmp_path):
    # Write a lock file with a dead PID
    path = tmp_path / "locks" / "backup.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    dead_pid = 99999999
    path.write_text(f"{dead_pid}\n{time.time()}\nbackup\n")

    info = lock.acquire("backup")
    assert info.pid == os.getpid()


def test_is_locked_false_when_no_file(lock):
    assert not lock.is_locked("missing")


def test_current_returns_none_when_no_lock(lock):
    assert lock.current("backup") is None


def test_current_returns_info_when_locked(lock):
    lock.acquire("backup")
    info = lock.current("backup")
    assert info is not None
    assert info.job_name == "backup"


def test_job_name_with_slashes_is_safe(lock):
    lock.acquire("jobs/nightly/backup")
    assert lock.is_locked("jobs/nightly/backup")
    lock.release("jobs/nightly/backup")
    assert not lock.is_locked("jobs/nightly/backup")


def test_pid_alive_current_process():
    assert _pid_alive(os.getpid())


def test_pid_alive_dead_pid():
    assert not _pid_alive(99999999)
