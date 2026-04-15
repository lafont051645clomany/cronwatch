"""Periodic digest report generation and delivery for cronwatch."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import List, Optional

from cronwatch.history import HistoryStore
from cronwatch.reporter import summarise_runs, format_report
from cronwatch.notifier import get_channel, NotificationResult
from cronwatch.config import CronwatchConfig


@dataclass
class DigestConfig:
    enabled: bool = False
    schedule: str = "daily"          # "hourly" | "daily" | "weekly"
    recipient: Optional[str] = None
    job_names: List[str] = field(default_factory=list)  # empty = all jobs


def _period_start(schedule: str, now: Optional[datetime.datetime] = None) -> datetime.datetime:
    """Return the start of the current digest period."""
    now = now or datetime.datetime.utcnow()
    if schedule == "hourly":
        return now.replace(minute=0, second=0, microsecond=0)
    if schedule == "weekly":
        monday = now - datetime.timedelta(days=now.weekday())
        return monday.replace(hour=0, minute=0, second=0, microsecond=0)
    # default: daily
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def build_digest(cfg: CronwatchConfig, digest_cfg: DigestConfig,
                 now: Optional[datetime.datetime] = None) -> str:
    """Collect history for the period and return a formatted digest string."""
    now = now or datetime.datetime.utcnow()
    since = _period_start(digest_cfg.schedule, now)

    all_runs = []
    job_names = digest_cfg.job_names or [j.name for j in cfg.jobs]
    for name in job_names:
        store = HistoryStore(name)
        runs = [r for r in store.load() if r.started_at and r.started_at >= since]
        all_runs.extend(runs)

    if not all_runs:
        return f"No runs recorded since {since.isoformat()} UTC."

    summaries = summarise_runs(all_runs)
    return format_report(summaries, title=f"Digest ({digest_cfg.schedule}) since {since.date()}")


def send_digest(cfg: CronwatchConfig, digest_cfg: DigestConfig,
               now: Optional[datetime.datetime] = None) -> NotificationResult:
    """Build and dispatch a digest via the configured notification channel."""
    body = build_digest(cfg, digest_cfg, now)
    subject = f"[cronwatch] {digest_cfg.schedule.capitalize()} Digest"

    channel = get_channel("email")
    if channel is None:
        return NotificationResult(success=False, channel="email",
                                  error="email channel not registered")
    return channel(subject=subject, body=body, config=cfg.alerts)
