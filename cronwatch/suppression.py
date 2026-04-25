"""Alert suppression rules: skip alerts that match user-defined conditions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from cronwatch.tracker import JobRun, JobStatus


@dataclass
class SuppressionRule:
    """A single suppression rule.

    A run is suppressed when *all* specified predicates match.
    """
    name: str
    job_names: List[str] = field(default_factory=list)   # empty → any job
    statuses: List[JobStatus] = field(default_factory=list)  # empty → any status
    max_duration: Optional[float] = None   # suppress if duration <= this (seconds)
    tags: List[str] = field(default_factory=list)          # empty → any tags
    reason: str = ""


def _matches(rule: SuppressionRule, run: JobRun) -> bool:
    """Return True when *run* satisfies every non-empty criterion in *rule*."""
    if rule.job_names and run.job_name not in rule.job_names:
        return False
    if rule.statuses and run.status not in rule.statuses:
        return False
    if rule.max_duration is not None:
        dur = run.duration_seconds()
        if dur is None or dur > rule.max_duration:
            return False
    if rule.tags:
        run_tags = set(getattr(run, "tags", []) or [])
        if not set(rule.tags).issubset(run_tags):
            return False
    return True


class Suppressor:
    """Holds a collection of suppression rules and evaluates them against runs."""

    def __init__(self) -> None:
        self._rules: List[SuppressionRule] = []

    def add_rule(self, rule: SuppressionRule) -> None:
        self._rules.append(rule)

    def is_suppressed(self, run: JobRun) -> Optional[SuppressionRule]:
        """Return the first matching rule, or None if the run should not be suppressed."""
        for rule in self._rules:
            if _matches(rule, run):
                return rule
        return None

    def filter_runs(
        self,
        runs: List[JobRun],
        *,
        on_suppressed: Optional[Callable[[JobRun, SuppressionRule], None]] = None,
    ) -> List[JobRun]:
        """Return only runs that are *not* suppressed.

        If *on_suppressed* is provided it is called for every suppressed run.
        """
        kept: List[JobRun] = []
        for run in runs:
            rule = self.is_suppressed(run)
            if rule is None:
                kept.append(run)
            elif on_suppressed is not None:
                on_suppressed(run, rule)
        return kept

    @property
    def rules(self) -> List[SuppressionRule]:
        return list(self._rules)
