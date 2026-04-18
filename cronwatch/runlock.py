"""Prevent concurrent execution of the same cron job via lock files."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class LockInfo:
    job_name: str
    pid: int
    acquired_at: float


class LockError(Exception):
    """Raised when a lock cannot be acquired."""


class RunLock:
    """File-based run lock for a single job."""

    def __init__(self, lock_dir: str | Path = "/tmp/cronwatch/locks") -> None:
        self._dir = Path(lock_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return self._dir / f"{safe}.lock"

    def acquire(self, job_name: str) -> LockInfo:
        """Acquire lock for job_name. Raises LockError if already locked."""
        path = self._path(job_name)
        if path.exists():
            info = self._read(path)
            if info and _pid_alive(info.pid):
                raise LockError(
                    f"Job '{job_name}' is already running (pid {info.pid})"
                )
            # stale lock — remove it
            path.unlink(missing_ok=True)

        info = LockInfo(job_name=job_name, pid=os.getpid(), acquired_at=time.time())
        path.write_text(f"{info.pid}\n{info.acquired_at}\n{info.job_name}\n")
        return info

    def release(self, job_name: str) -> None:
        """Release lock for job_name (no-op if not held)."""
        self._path(job_name).unlink(missing_ok=True)

    def is_locked(self, job_name: str) -> bool:
        path = self._path(job_name)
        if not path.exists():
            return False
        info = self._read(path)
        return info is not None and _pid_alive(info.pid)

    def current(self, job_name: str) -> Optional[LockInfo]:
        path = self._path(job_name)
        if not path.exists():
            return None
        return self._read(path)

    @staticmethod
    def _read(path: Path) -> Optional[LockInfo]:
        try:
            lines = path.read_text().splitlines()
            pid = int(lines[0])
            acquired_at = float(lines[1])
            job_name = lines[2]
            return LockInfo(job_name=job_name, pid=pid, acquired_at=acquired_at)
        except Exception:
            return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
