"""Alert deduplication and anomaly suppression for cronwatch."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from cronwatch.tracker import JobRun


@dataclass
class AnomalyRecord:
    job_name: str
    first_seen: datetime
    last_seen: datetime
    count: int = 1
    suppressed: int = 0


@dataclass
class AnomalyTracker:
    """Track repeated anomalies and suppress duplicate alerts."""
    window: timedelta = timedelta(hours=1)
    threshold: int = 3  # suppress after this many occurrences
    _records: Dict[str, AnomalyRecord] = field(default_factory=dict)

    def _evict(self, now: datetime) -> None:
        cutoff = now - self.window
        self._records = {
            k: v for k, v in self._records.items()
            if v.last_seen >= cutoff
        }

    def record(self, run: JobRun, now: Optional[datetime] = None) -> bool:
        """Record an anomalous run. Returns True if alert should fire."""
        now = now or datetime.utcnow()
        self._evict(now)
        key = run.job_name
        if key not in self._records:
            self._records[key] = AnomalyRecord(
                job_name=key, first_seen=now, last_seen=now
            )
            return True
        rec = self._records[key]
        rec.last_seen = now
        rec.count += 1
        if rec.count > self.threshold:
            rec.suppressed += 1
            return False
        return True

    def get(self, job_name: str) -> Optional[AnomalyRecord]:
        return self._records.get(job_name)

    def active_anomalies(self) -> List[AnomalyRecord]:
        now = datetime.utcnow()
        self._evict(now)
        return list(self._records.values())

    def reset(self, job_name: str) -> None:
        self._records.pop(job_name, None)
