"""Notification channel registry with optional rate-limit integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from cronwatch.alerts import dispatch_alert
from cronwatch.config import AlertConfig
from cronwatch.ratelimit import RateLimiter, RateLimitConfig
from cronwatch.tracker import JobRun

# Type alias for a channel handler
ChannelFn = Callable[[JobRun, AlertConfig], bool]

_REGISTRY: Dict[str, ChannelFn] = {}


def register_channel(name: str, fn: ChannelFn) -> None:
    """Register a notification channel under *name*."""
    _REGISTRY[name] = fn


def get_channel(name: str) -> Optional[ChannelFn]:
    """Return the channel function for *name*, or None."""
    return _REGISTRY.get(name)


def list_channels() -> List[str]:
    """Return sorted list of registered channel names."""
    return sorted(_REGISTRY.keys())


@dataclass
class NotificationResult:
    channel: str
    success: bool
    skipped: bool = False
    error: Optional[str] = None


@dataclass
class NotificationSummary:
    job: str
    results: List[NotificationResult] = field(default_factory=list)

    @property
    def any_sent(self) -> bool:
        return any(r.success for r in self.results)

    @property
    def all_skipped(self) -> bool:
        return all(r.skipped for r in self.results)


def notify(
    run: JobRun,
    alert_cfg: AlertConfig,
    channels None,
    rate_limiter: Optional[RateLimiter] = None,
) -> NotificationSummary:
    """Dispatch *run* alert through each requested channel.

    If *rate_limiter* is provided, alerts are skipped when the limiter
    blocks them and recorded when they are sent.
    """
    summary = NotificationSummary(job=run.job_name)
    targets = channels if channels is not None else list_channels()

    for name in targets:
        fn = get_channel(name)
        if fn is None:
            summary.results.append(
                NotificationResult(channel=name, success=False, error="unknown channel")
            )
            continue

        if rate_limiter and not rate_limiter.is_allowed(run.job_name):
            summary.results.append(
                NotificationResult(channel=name, success=False, skipped=True)
            )
            continue

        try:
            ok = fn(run, alert_cfg)
            if rate_limiter and ok:
                rate_limiter.record(run.job_name)
            summary.results.append(NotificationResult(channel=name, success=ok))
        except Exception as exc:  # noqa: BLE001
            summary.results.append(
                NotificationResult(channel=name, success=False, error=str(exc))
            )

    return summary


# Register the built-in e-mail channel
register_channel("email", lambda run, cfg: (dispatch_alert(run, cfg), True)[1])
