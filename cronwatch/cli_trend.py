"""CLI subcommand: cronwatch trend."""
from __future__ import annotations
import argparse
from cronwatch.history import HistoryStore
from cronwatch.trend import analyse_trend
from cronwatch.trend_reporter import format_trend_table


def add_trend_subparser(subparsers) -> None:
    p = subparsers.add_parser('trend', help='Analyse job duration/failure trends')
    p.add_argument('--history', default='cronwatch_history.json', help='History file')
    p.add_argument('--job', help='Limit to a specific job name')
    p.add_argument('--min-samples', type=int, default=5, help='Min runs required')
    p.add_argument('--slope-threshold', type=float, default=1.0,
                   help='Seconds/run slope to flag as degrading')
    p.set_defaults(func=cmd_trend)


def cmd_trend(args: argparse.Namespace) -> None:
    store = HistoryStore(args.history)
    runs = store.load()

    job_names = {r.job_name for r in runs}
    if args.job:
        job_names = {j for j in job_names if j == args.job}

    results = [
        analyse_trend(runs, name, args.min_samples, args.slope_threshold)
        for name in sorted(job_names)
    ]
    print(format_trend_table(results))
