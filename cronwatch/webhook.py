"""Webhook notification channel for cronwatch alerts."""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any

from cronwatch.tracker import JobRun


@dataclass
class WebhookConfig:
    url: str
    method: str = "POST"
    headers: dict[str, str] = field(default_factory=dict)
    timeout: int = 10
    include_run_details: bool = True


@dataclass
class WebhookResult:
    url: str
    status_code: int | None
    success: bool
    error: str | None = None


def _build_payload(run: JobRun, cfg: WebhookConfig) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "job": run.job_name,
        "status": run.status.value,
    }
    if cfg.include_run_details:
        payload["started_at"] = run.started_at.isoformat() if run.started_at else None
        payload["finished_at"] = run.finished_at.isoformat() if run.finished_at else None
        payload["exit_code"] = run.exit_code
        payload["error"] = run.error
    return payload


def send_webhook(run: JobRun, cfg: WebhookConfig) -> WebhookResult:
    """POST a JSON payload to the configured webhook URL."""
    payload = _build_payload(run, cfg)
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", **cfg.headers}
    req = urllib.request.Request(
        cfg.url, data=body, headers=headers, method=cfg.method
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout) as resp:
            return WebhookResult(url=cfg.url, status_code=resp.status, success=True)
    except urllib.error.HTTPError as exc:
        return WebhookResult(
            url=cfg.url, status_code=exc.code, success=False, error=str(exc)
        )
    except Exception as exc:  # noqa: BLE001
        return WebhookResult(url=cfg.url, status_code=None, success=False, error=str(exc))
