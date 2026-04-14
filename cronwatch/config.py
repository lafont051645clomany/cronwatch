"""Configuration loading and validation for cronwatch."""

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


DEFAULT_CONFIG_PATHS = [
    Path("cronwatch.toml"),
    Path(".cronwatch.toml"),
    Path("~/.config/cronwatch/config.toml").expanduser(),
]


@dataclass
class JobConfig:
    name: str
    schedule: str
    max_duration: int = 3600  # seconds
    alert_on_failure: bool = True
    alert_on_delay: bool = True
    timeout: Optional[int] = None
    tags: list[str] = field(default_factory=list)


@dataclass
class AlertConfig:
    email: Optional[str] = None
    webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None


@dataclass
class CronwatchConfig:
    jobs: list[JobConfig] = field(default_factory=list)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    log_file: str = "cronwatch.log"
    check_interval: int = 60  # seconds


def load_config(config_path: Optional[str] = None) -> CronwatchConfig:
    """Load configuration from a TOML file."""
    path: Optional[Path] = None

    if config_path:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
    else:
        for candidate in DEFAULT_CONFIG_PATHS:
            if candidate.exists():
                path = candidate
                break

    if path is None:
        return CronwatchConfig()

    with open(path, "rb") as f:
        raw = tomllib.load(f)

    jobs = [
        JobConfig(
            name=j["name"],
            schedule=j["schedule"],
            max_duration=j.get("max_duration", 3600),
            alert_on_failure=j.get("alert_on_failure", True),
            alert_on_delay=j.get("alert_on_delay", True),
            timeout=j.get("timeout"),
            tags=j.get("tags", []),
        )
        for j in raw.get("jobs", [])
    ]

    raw_alerts = raw.get("alerts", {})
    alerts = AlertConfig(
        email=raw_alerts.get("email"),
        webhook_url=raw_alerts.get("webhook_url"),
        slack_channel=raw_alerts.get("slack_channel"),
    )

    return CronwatchConfig(
        jobs=jobs,
        alerts=alerts,
        log_file=raw.get("log_file", "cronwatch.log"),
        check_interval=raw.get("check_interval", 60),
    )
