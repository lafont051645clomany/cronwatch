"""CLI sub-command: throttle — show current alert throttle state."""
from __future__ import annotations

import argparse

from cronwatch.config import load_config
from cronwatch.history import HistoryStore
from cronwatch.throttle import ThrottleConfig, Throttler
from cronwatch.throttle_reporter import format_throttle_table


def add_throttle_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("throttle", help="Show alert throttle state")
    p.add_argument("--config", default=None, help="Path to cronwatch.toml")
    p.add_argument(
        "--window",
        type=int,
        default=None,
        help="Override throttle window in seconds",
    )
    p.add_argument(
        "--max-alerts",
        type=int,
        default=None,
        help="Override max alerts per window",
    )
    p.set_defaults(func=cmd_throttle)


def cmd_throttle(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    window = args.window or 300
    max_alerts = args.max_alerts or 3
    tcfg = ThrottleConfig(window_seconds=window, max_alerts=max_alerts)
    throttler = Throttler(tcfg)

    store = HistoryStore(cfg.history_path if hasattr(cfg, "history_path") else "cronwatch_history.json")
    runs = store.load()
    job_names = list({r.job_name for r in runs})
    print(format_throttle_table(throttler, job_names))
