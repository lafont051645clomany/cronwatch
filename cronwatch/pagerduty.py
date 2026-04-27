"""PagerDuty notification channel for cronwatch alerts."""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional

from cronwatch.tracker import JobRun, JobStatus
from cronwatch.notifier import NotificationResult


_EVENTS_API = "https://events.pagerduty.com/v2/enqueue"

_SEVERITY_MAP = {
    JobStatus.FAILED: "error",
    JobStatus.TIMEOUT: "warning",
    JobStatus.SUCCESS: "info",
}


@dataclass
class PagerDutyConfig:
    routing_key: str
    source: str = "cronwatch"
    component: str = "cron"
    timeout_seconds: int = 10
    extra_details: dict = field(default_factory=dict)


def _build_payload(run: JobRun, cfg: PagerDutyConfig) -> dict:
    severity = _SEVERITY_MAP.get(run.status, "error")
    summary = f"[cronwatch] {run.job_name} {run.status.value}"
    if run.exit_code is not None:
        summary += f" (exit {run.exit_code})"

    details: dict = {
        "job": run.job_name,
        "status": run.status.value,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "exit_code": run.exit_code,
        "error": run.error,
    }
    details.update(cfg.extra_details)

    return {
        "routing_key": cfg.routing_key,
        "event_action": "trigger",
        "payload": {
            "summary": summary,
            "severity": severity,
            "source": cfg.source,
            "component": cfg.component,
            "custom_details": details,
        },
        "dedup_key": f"cronwatch-{run.job_name}-{run.run_id}",
    }


def send_pagerduty_alert(
    run: JobRun,
    cfg: PagerDutyConfig,
    *,
    api_url: str = _EVENTS_API,
) -> NotificationResult:
    """Send a PagerDuty event for *run* and return a NotificationResult."""
    payload = _build_payload(run, cfg)
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        api_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
            status_code: Optional[int] = resp.status
    except urllib.error.HTTPError as exc:
        return NotificationResult(
            channel="pagerduty",
            success=False,
            error=f"HTTP {exc.code}: {exc.reason}",
        )
    except Exception as exc:  # noqa: BLE001
        return NotificationResult(
            channel="pagerduty",
            success=False,
            error=str(exc),
        )

    return NotificationResult(
        channel="pagerduty",
        success=True,
        detail=f"HTTP {status_code}",
    )
