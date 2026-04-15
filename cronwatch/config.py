"""Configuration loading for cronwatch."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

DEFAULT_CONFIG_PATH = "cronwatch.toml"


@dataclass
class JobConfig:
    name: str
    schedule: str = ""
    timeout: int = 3600          # seconds
    grace: int = 300             # seconds after expected run before alerting
    enabled: bool = True


@dataclass
class AlertConfig:
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_address: str = "cronwatch@localhost"
    to_addresses: List[str] = field(default_factory=list)
    use_tls: bool = False


@dataclass
class DigestConfig:
    enabled: bool = False
    schedule: str = "daily"
    recipient: Optional[str] = None
    job_names: List[str] = field(default_factory=list)


@dataclass
class CronwatchConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    digest: DigestConfig = field(default_factory=DigestConfig)
    history_dir: str = ".cronwatch"
    log_level: str = "INFO"


def _parse_jobs(raw: list) -> List[JobConfig]:
    return [
        JobConfig(
            name=j["name"],
            schedule=j.get("schedule", ""),
            timeout=j.get("timeout", 3600),
            grace=j.get("grace", 300),
            enabled=j.get("enabled", True),
        )
        for j in raw
    ]


def _parse_alerts(raw: dict) -> AlertConfig:
    return AlertConfig(
        smtp_host=raw.get("smtp_host", "localhost"),
        smtp_port=raw.get("smtp_port", 25),
        smtp_user=raw.get("smtp_user"),
        smtp_password=raw.get("smtp_password"),
        from_address=raw.get("from_address", "cronwatch@localhost"),
        to_addresses=raw.get("to_addresses", []),
        use_tls=raw.get("use_tls", False),
    )


def _parse_digest(raw: dict) -> DigestConfig:
    return DigestConfig(
        enabled=raw.get("enabled", False),
        schedule=raw.get("schedule", "daily"),
        recipient=raw.get("recipient"),
        job_names=raw.get("job_names", []),
    )


def load_config(path: Optional[str] = None) -> CronwatchConfig:
    if path is not None and not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    if path is None and not os.path.exists(DEFAULT_CONFIG_PATH):
        return CronwatchConfig()

    config_path = path or DEFAULT_CONFIG_PATH
    with open(config_path, "rb") as fh:
        data = tomllib.load(fh)

    return CronwatchConfig(
        jobs=_parse_jobs(data.get("jobs", [])),
        alerts=_parse_alerts(data.get("alerts", {})),
        digest=_parse_digest(data.get("digest", {})),
        history_dir=data.get("history_dir", ".cronwatch"),
        log_level=data.get("log_level", "INFO"),
    )
