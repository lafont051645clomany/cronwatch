"""Lifecycle hooks for cronwatch job events.

Allows external code (plugins, scripts) to register callbacks that fire
when a job starts, succeeds, fails, or times out.
"""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import Callable, Dict, List

from cronwatch.tracker import JobRun

logger = logging.getLogger(__name__)


class HookEvent(str, Enum):
    JOB_START = "job_start"
    JOB_SUCCESS = "job_success"
    JOB_FAILURE = "job_failure"
    JOB_TIMEOUT = "job_timeout"


HookCallback = Callable[[JobRun], None]

_hooks: Dict[HookEvent, List[HookCallback]] = {event: [] for event in HookEvent}


def on(event: HookEvent) -> Callable[[HookCallback], HookCallback]:
    """Decorator to register a callback for a specific lifecycle event.

    Usage::

        @on(HookEvent.JOB_FAILURE)
        def my_handler(run: JobRun) -> None:
            print(f"Job {run.job_name} failed!")
    """
    def decorator(fn: HookCallback) -> HookCallback:
        register(event, fn)
        return fn
    return decorator


def register(event: HookEvent, callback: HookCallback) -> None:
    """Register *callback* to be invoked when *event* fires."""
    _hooks[event].append(callback)
    logger.debug("Hook registered for event '%s': %s", event.value, callback.__name__)


def unregister(event: HookEvent, callback: HookCallback) -> bool:
    """Remove *callback* from *event*. Returns True if it was present."""
    try:
        _hooks[event].remove(callback)
        return True
    except ValueError:
        return False


def fire(event: HookEvent, run: JobRun) -> None:
    """Invoke all callbacks registered for *event*.

    Exceptions raised by individual callbacks are logged but do not
    prevent remaining callbacks from executing.
    """
    for callback in list(_hooks[event]):
        try:
            callback(run)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "Hook callback '%s' for event '%s' raised: %s",
                callback.__name__,
                event.value,
                exc,
            )


def clear(event: HookEvent | None = None) -> None:
    """Remove all hooks, optionally scoped to a single event."""
    if event is None:
        for ev in HookEvent:
            _hooks[ev].clear()
    else:
        _hooks[event].clear()
