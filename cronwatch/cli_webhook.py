"""CLI sub-command: webhook — test or list webhook deliveries."""
from __future__ import annotations

import argparse

from cronwatch.config import load_config
from cronwatch.history import HistoryStore
from cronwatch.webhook import WebhookConfig, send_webhook
from cronwatch.webhook_reporter import format_webhook_results


def add_webhook_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("webhook", help="Test webhook delivery for a job run")
    p.add_argument("--config", default=None, help="Path to cronwatch.toml")
    p.add_argument("--job", required=True, help="Job name to look up last run")
    p.add_argument("--url", required=True, help="Webhook URL to POST to")
    p.add_argument(
        "--no-details",
        dest="no_details",
        action="store_true",
        help="Omit run details from payload",
    )
    p.set_defaults(func=cmd_webhook)


def cmd_webhook(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    store = HistoryStore(cfg.history_path)
    runs = [r for r in store.load() if r.job_name == args.job]
    if not runs:
        print(f"No runs found for job '{args.job}'.")
        return 1

    run = sorted(runs, key=lambda r: r.started_at or r.finished_at)[-1]
    wh_cfg = WebhookConfig(
        url=args.url,
        include_run_details=not args.no_details,
    )
    result = send_webhook(run, wh_cfg)
    print(format_webhook_results([result]))
    return 0 if result.success else 1
