"""Configuration loading and validation for cronwatch."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cronwatch.retry import RetryPolicy

DEFAULT_CONFIG_PATHS = ["cronwatch.toml", "~/.cronwatch.toml"]


@dataclass
class JobConfig:
    name: str
    schedule: str
    timeout_seconds: int = 3600
    grace_seconds: int = 300
    retry: RetryPolicy = field(default_factory=RetryPolicy)


@dataclass
class AlertConfig:
    email: Optional[str] = None
    smtp_host: str = "localhost"
    smtp_port: int = 25
    from_address: str = "cronwatch@localhost"


@dataclass
class DigestConfig:
    enabled: bool = False
    period: str = "daily"  # "hourly" | "daily"
    email: Optional[str] = None


@dataclass
class CronwatchConfig:
    jobs: list[JobConfig] = field(default_factory=list)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    digest: DigestConfig = field(default_factory=DigestConfig)
    history_path: str = "~/.cronwatch_history.json"
    log_level: str = "INFO"


# ---------------------------------------------------------------------------
# Internal parsers
# ---------------------------------------------------------------------------

def _parse_retry(raw: dict) -> RetryPolicy:
    return RetryPolicy(
        max_attempts=raw.get("max_attempts", 3),
        delay_seconds=float(raw.get("delay_seconds", 5.0)),
        backoff_factor=float(raw.get("backoff_factor", 2.0)),
        max_delay_seconds=float(raw.get("max_delay_seconds", 60.0)),
    )


def _parse_jobs(raw_jobs: list[dict]) -> list[JobConfig]:
    jobs = []
    for raw in raw_jobs:
        retry = _parse_retry(raw.get("retry", {}))
        jobs.append(
            JobConfig(
                name=raw["name"],
                schedule=raw["schedule"],
                timeout_seconds=raw.get("timeout_seconds", 3600),
                grace_seconds=raw.get("grace_seconds", 300),
                retry=retry,
            )
        )
    return jobs


def _parse_alerts(raw: dict) -> AlertConfig:
    return AlertConfig(
        email=raw.get("email"),
        smtp_host=raw.get("smtp_host", "localhost"),
        smtp_port=int(raw.get("smtp_port", 25)),
        from_address=raw.get("from_address", "cronwatch@localhost"),
    )


def _parse_digest(raw: dict) -> DigestConfig:
    return DigestConfig(
        enabled=raw.get("enabled", False),
        period=raw.get("period", "daily"),
        email=raw.get("email"),
    )


# ---------------------------------------------------------------------------
# Public loader
# ---------------------------------------------------------------------------

def load_config(path: Optional[str] = None) -> CronwatchConfig:
    """Load configuration from a TOML file.

    If *path* is given and does not exist, raises FileNotFoundError.
    If *path* is None, the default search paths are tried; missing defaults
    are silently ignored and an empty config is returned.
    """
    if path is not None:
        config_path = Path(path).expanduser()
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
    else:
        config_path = None
        for candidate in DEFAULT_CONFIG_PATHS:
            p = Path(candidate).expanduser()
            if p.exists():
                config_path = p
                break
        if config_path is None:
            return CronwatchConfig()

    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)

    return CronwatchConfig(
        jobs=_parse_jobs(raw.get("jobs", [])),
        alerts=_parse_alerts(raw.get("alerts", {})),
        digest=_parse_digest(raw.get("digest", {})),
        history_path=raw.get("history_path", "~/.cronwatch_history.json"),
        log_level=raw.get("log_level", "INFO"),
    )
