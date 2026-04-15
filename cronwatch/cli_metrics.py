"""CLI sub-command: cronwatch metrics — show aggregated job metrics."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronwatch.config import CronwatchConfig
from cronwatch.history import HistoryStore
from cronwatch.metrics import compute_metrics, top_failing_jobs
from cronwatch.metrics_reporter import format_metrics_table, format_top_failing


def add_metrics_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("metrics", help="Show aggregated job run metrics")
    p.add_argument("--config", metavar="FILE", help="Path to cronwatch.toml")
    p.add_argument(
        "--job", metavar="NAME", help="Restrict output to a single job"
    )
    p.add_argument(
        "--top-failing",
        metavar="N",
        type=int,
        default=0,
        help="Show the top-N failing jobs",
    )
    p.set_defaults(func=cmd_metrics)


def cmd_metrics(args: argparse.Namespace) -> int:
    cfg = CronwatchConfig.load(args.config if hasattr(args, "config") else None)
    history_path = Path(cfg.history_path) if cfg.history_path else Path("cronwatch_history.json")
    store = HistoryStore(history_path)
    runs = store.load()

    if args.job:
        runs = [r for r in runs if r.job_name == args.job]

    metrics = compute_metrics(runs)

    if args.top_failing:
        top = top_failing_jobs(metrics, n=args.top_failing)
        print(format_top_failing(top))
        return 0

    print(format_metrics_table(metrics))
    return 0
