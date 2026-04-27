"""CLI sub-command: ``cronwatch sla`` — report SLA violations."""
from __future__ import annotations

import argparse
from typing import List

from cronwatch.config import CronwatchConfig
from cronwatch.history import HistoryStore
from cronwatch.sla import SLAChecker, SLAConfig
from cronwatch.sla_reporter import format_sla_table


def add_sla_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("sla", help="Report SLA violations")
    p.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help="Path to cronwatch.toml",
    )
    p.add_argument(
        "--job",
        metavar="NAME",
        default=None,
        help="Limit report to a single job",
    )
    p.set_defaults(func=cmd_sla)


def cmd_sla(args: argparse.Namespace, cfg: CronwatchConfig) -> int:
    store = HistoryStore(cfg.history_path)
    runs = store.load()

    sla_configs: List[SLAConfig] = [
        SLAConfig(
            job_name=job.name,
            min_success_rate=getattr(job, "sla_min_success_rate", 0.95),
            max_duration_seconds=getattr(job, "sla_max_duration_seconds", None),
            window_hours=getattr(job, "sla_window_hours", 24.0),
        )
        for job in cfg.jobs
        if args.job is None or job.name == args.job
    ]

    checker = SLAChecker(sla_configs)
    violations = checker.check_all(runs)
    print(format_sla_table(violations))
    return 1 if violations else 0
