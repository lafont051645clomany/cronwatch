"""Alert escalation: track repeated failures and escalate after a threshold."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class EscalationPolicy:
    threshold: int = 3          # consecutive failures before escalating
    escalation_emails: List[str] = field(default_factory=list)


@dataclass
class EscalationState:
    job_name: str
    consecutive_failures: int = 0
    escalated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    @property
    def is_escalated(self) -> bool:
        return self.escalated_at is not None and self.resolved_at is None


class EscalationTracker:
    def __init__(self, policy: EscalationPolicy) -> None:
        self.policy = policy
        self._states: Dict[str, EscalationState] = {}

    def _get(self, job_name: str) -> EscalationState:
        if job_name not in self._states:
            self._states[job_name] = EscalationState(job_name=job_name)
        return self._states[job_name]

    def record_failure(self, job_name: str, now: Optional[datetime] = None) -> EscalationState:
        now = now or datetime.utcnow()
        state = self._get(job_name)
        state.consecutive_failures += 1
        if (
            not state.is_escalated
            and state.consecutive_failures >= self.policy.threshold
        ):
            state.escalated_at = now
            state.resolved_at = None
        return state

    def record_success(self, job_name: str, now: Optional[datetime] = None) -> EscalationState:
        now = now or datetime.utcnow()
        state = self._get(job_name)
        if state.is_escalated:
            state.resolved_at = now
        state.consecutive_failures = 0
        return state

    def get_state(self, job_name: str) -> Optional[EscalationState]:
        return self._states.get(job_name)

    def all_escalated(self) -> List[EscalationState]:
        return [s for s in self._states.values() if s.is_escalated]
