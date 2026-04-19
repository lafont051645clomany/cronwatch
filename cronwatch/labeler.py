"""Automatic run labeling based on duration and status thresholds."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronwatch.tracker import JobRun, JobStatus


@dataclass
class LabelRule:
    label: str
    status: Optional[JobStatus] = None          # match on status
    min_duration: Optional[float] = None        # seconds
    max_duration: Optional[float] = None        # seconds

    def matches(self, run: JobRun) -> bool:
        if self.status is not None and run.status != self.status:
            return False
        dur = run.duration_seconds()
        if self.min_duration is not None and (dur is None or dur < self.min_duration):
            return False
        if self.max_duration is not None and (dur is None or dur > self.max_duration):
            return False
        return True


@dataclass
class Labeler:
    rules: List[LabelRule] = field(default_factory=list)

    def add_rule(self, rule: LabelRule) -> None:
        self.rules.append(rule)

    def label(self, run: JobRun) -> List[str]:
        """Return all labels whose rules match *run*."""
        return [r.label for r in self.rules if r.matches(run)]

    def label_all(self, runs: List[JobRun]) -> dict[str, List[str]]:
        """Return mapping of run id -> labels for a list of runs."""
        return {id(run): self.label(run) for run in runs}


# ---------------------------------------------------------------------------
# Convenience factory with sensible built-in rules
# ---------------------------------------------------------------------------

def default_labeler() -> Labeler:
    lb = Labeler()
    lb.add_rule(LabelRule(label="failed", status=JobStatus.FAILURE))
    lb.add_rule(LabelRule(label="slow", min_duration=300.0))   # >5 min
    lb.add_rule(LabelRule(label="fast", max_duration=5.0))     # <5 s
    lb.add_rule(LabelRule(label="timeout", status=JobStatus.TIMEOUT))
    return lb
