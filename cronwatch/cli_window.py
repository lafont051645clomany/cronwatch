"""CLI sub-command: cronwatch window — show sliding-window stats."""
from __future__ import annotations

import argparse
import sys

from cronwatch.history import HistoryStore
from cronwatch.window import WindowConfig, compute_all
from cronwatch.window_reporter import format_window_table


def add_window_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "window",
        help="Show sliding-window statistics for recent job runs.",
    )
    p.add_argument(
        "--minutes",
        type=int,
        default=60,
        metavar="N",
        help="Window size in minutes (default: 60).",
    )
    p.add_argument(
        "--job",
        metavar="NAME",
        help="Restrict output to a single job.",
    )
    p.add_argument(
        "--history",
        default="cronwatch_history.json",
        metavar="FILE",
        help="Path to history file.",
    )
    p.set_defaults(func=cmd_window)


def cmd_window(args: argparse.Namespace) -> None:
    store = HistoryStore(args.history)
    runs = store.load()

    if args.job:
        runs = [r for r in runs if r.job_name == args.job]

    if not runs:
        print("No runs found.", file=sys.stderr)
        return

    cfg = WindowConfig(size_minutes=args.minutes)
    stats = compute_all(runs, cfg)
    print(format_window_table(stats, args.minutes))
