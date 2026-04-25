"""Dead-letter queue for failed alert dispatches.

When an alert cannot be delivered (e.g. SMTP down), the attempt is
recorded here so it can be replayed later.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DeadLetter:
    job_name: str
    subject: str
    body: str
    queued_at: datetime
    attempts: int = 0
    last_error: Optional[str] = None


def _to_dict(dl: DeadLetter) -> dict:
    d = asdict(dl)
    d["queued_at"] = dl.queued_at.isoformat()
    return d


def _from_dict(d: dict) -> DeadLetter:
    d = dict(d)
    d["queued_at"] = datetime.fromisoformat(d["queued_at"])
    return DeadLetter(**d)


class DeadLetterQueue:
    """Persistent queue stored as a JSON-lines file."""

    def __init__(self, path: str = "cronwatch_deadletter.jsonl") -> None:
        self._path = Path(path)

    # ------------------------------------------------------------------
    def push(self, job_name: str, subject: str, body: str,
             error: Optional[str] = None) -> DeadLetter:
        """Append a new failed-delivery record."""
        dl = DeadLetter(
            job_name=job_name,
            subject=subject,
            body=body,
            queued_at=_now(),
            attempts=1,
            last_error=error,
        )
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(_to_dict(dl)) + "\n")
        return dl

    def load(self) -> List[DeadLetter]:
        """Return all queued letters."""
        if not self._path.exists():
            return []
        letters: List[DeadLetter] = []
        with self._path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    letters.append(_from_dict(json.loads(line)))
        return letters

    def clear(self) -> int:
        """Delete all queued letters; return how many were removed."""
        letters = self.load()
        if self._path.exists():
            self._path.unlink()
        return len(letters)

    def retry_all(self, dispatch_fn) -> dict:
        """Attempt to replay every queued letter via *dispatch_fn*.

        *dispatch_fn* must accept (subject, body) and return True on success.
        Returns {"replayed": int, "failed": int}.
        """
        letters = self.load()
        if not letters:
            return {"replayed": 0, "failed": 0}

        replayed, failed_letters = 0, []
        for dl in letters:
            try:
                ok = dispatch_fn(dl.subject, dl.body)
            except Exception as exc:  # noqa: BLE001
                ok = False
                dl.last_error = str(exc)
            if ok:
                replayed += 1
            else:
                dl.attempts += 1
                failed_letters.append(dl)

        # Rewrite file with only the still-failed letters
        if self._path.exists():
            self._path.unlink()
        for dl in failed_letters:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(_to_dict(dl)) + "\n")

        return {"replayed": replayed, "failed": len(failed_letters)}
