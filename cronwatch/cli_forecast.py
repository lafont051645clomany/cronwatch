"""CLI sub-command: cronwatch forecast."""
from __future__ import annotations

import argparse
from typing import List

from cronwatch.forecast import forecast
from cronwatch.forecast_reporter import format_forecast_table
from cronwatch.history import HistoryStore


def add_forecast_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "forecast",
        help="Predict future failure rates from run history.",
    )
    p.add_argument(
        "--history",
        default="cronwatch_history.json",
        metavar="FILE",
        help="Path to history file (default: cronwatch_history.json).",
    )
    p.add_argument(
        "--job",
        metavar="NAME",
        help="Forecast a single job; omit to forecast all jobs.",
    )
    p.set_defaults(func=cmd_forecast)


def cmd_forecast(args: argparse.Namespace) -> None:
    store = HistoryStore(args.history)
    runs = store.load()

    if args.job:
        job_names: List[str] = [args.job]
    else:
        seen: dict[str, bool] = {}
        job_names = [r.job_name for r in runs if not seen.setdefault(r.job_name, True) or True]
        # deduplicate preserving order
        job_names = list(dict.fromkeys(r.job_name for r in runs))

    results = [forecast(name, runs) for name in job_names]
    print(format_forecast_table(results))
