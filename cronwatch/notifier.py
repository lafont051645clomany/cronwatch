"""Notification channel registry and dispatcher for cronwatch."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from cronwatch.alerts import dispatch_alert
from cronwatch.config import AlertConfig
from cronwatch.tracker import JobRun

logger = logging.getLogger(__name__)

# Type alias for a notification handler
NotifyHandler = Callable[[JobRun, AlertConfig], bool]

_REGISTRY: Dict[str, NotifyHandler] = {}


def register_channel(name: str, handler: NotifyHandler) -> None:
    """Register a notification channel handler by name."""
    _REGISTRY[name] = handler
    logger.debug("Registered notification channel: %s", name)


def get_channel(name: str) -> Optional[NotifyHandler]:
    """Return a registered handler or None."""
    return _REGISTRY.get(name)


def list_channels() -> List[str]:
    """Return names of all registered channels."""
    return list(_REGISTRY.keys())


@dataclass
class NotificationResult:
    channel: str
    success: bool
    error: Optional[str] = None


@dataclass
class NotificationSummary:
    run: JobRun
    results: List[NotificationResult] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        return all(r.success for r in self.results)

    @property
    def failed_channels(self) -> List[str]:
        return [r.channel for r in self.results if not r.success]


def notify(run: JobRun, alert_cfg: AlertConfig, channels: Optional[List[str]] = None) -> NotificationSummary:
    """Dispatch notifications for a job run across one or more channels.

    Falls back to the built-in email dispatcher when no channels are specified
    or when the 'email' channel is requested but not explicitly registered.
    """
    summary = NotificationSummary(run=run)
    targets = channels or list_channels() or ["email"]

    for channel in targets:
        handler = get_channel(channel)
        if handler is None and channel == "email":
            # Use the default email dispatcher from alerts module
            handler = lambda r, a: dispatch_alert(r, a)  # noqa: E731
        if handler is None:
            logger.warning("No handler registered for channel '%s'; skipping.", channel)
            summary.results.append(NotificationResult(channel=channel, success=False, error="unregistered channel"))
            continue
        try:
            ok = handler(run, alert_cfg)
            summary.results.append(NotificationResult(channel=channel, success=bool(ok)))
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Channel '%s' raised an exception: %s", channel, exc)
            summary.results.append(NotificationResult(channel=channel, success=False, error=str(exc)))

    return summary


# Register the built-in email channel on import
register_channel("email", lambda run, cfg: dispatch_alert(run, cfg))
