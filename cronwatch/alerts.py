"""Alert dispatcher: sends notifications when jobs fail, timeout, or run late."""

from __future__ import annotations

import smtplib
import logging
from email.message import EmailMessage
from typing import Optional

from cronwatch.config import AlertConfig
from cronwatch.tracker import JobRun, JobStatus

logger = logging.getLogger(__name__)


def _build_subject(run: JobRun) -> str:
    status_label = run.status.value.upper()
    return f"[cronwatch] {status_label}: {run.job_name}"


def _build_body(run: JobRun) -> str:
    lines = [
        f"Job:     {run.job_name}",
        f"Status:  {run.status.value}",
        f"Started: {run.started_at.isoformat()}Z",
    ]
    if run.finished_at:
        lines.append(f"Ended:   {run.finished_at.isoformat()}Z")
    if run.duration_seconds is not None:
        lines.append(f"Duration: {run.duration_seconds:.1f}s")
    if run.exit_code is not None:
        lines.append(f"Exit code: {run.exit_code}")
    return "\n".join(lines)


def send_email_alert(run: JobRun, cfg: AlertConfig) -> bool:
    """Send an email alert. Returns True on success."""
    if not cfg.email_to or not cfg.smtp_host:
        logger.debug("Email alert skipped: missing email_to or smtp_host.")
        return False

    msg = EmailMessage()
    msg["Subject"] = _build_subject(run)
    msg["From"] = cfg.email_from or "cronwatch@localhost"
    msg["To"] = ", ".join(cfg.email_to)
    msg.set_content(_build_body(run))

    try:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port or 25) as server:
            if cfg.smtp_user and cfg.smtp_password:
                server.login(cfg.smtp_user, cfg.smtp_password)
            server.send_message(msg)
        logger.info("Alert email sent for job '%s' (%s).", run.job_name, run.status.value)
        return True
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to send alert email: %s", exc)
        return False


def dispatch_alert(run: JobRun, cfg: AlertConfig) -> None:
    """Dispatch all configured alerts for a job run."""
    alertable = {JobStatus.FAILED, JobStatus.TIMEOUT}
    if run.status not in alertable:
        return
    send_email_alert(run, cfg)
