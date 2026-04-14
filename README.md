# cronwatch

A lightweight CLI tool to monitor cron job execution times and alert on unexpected delays or failures.

---

## Installation

```bash
pip install cronwatch
```

Or install from source:

```bash
git clone https://github.com/youruser/cronwatch.git && cd cronwatch && pip install .
```

---

## Usage

Wrap your cron job command with `cronwatch` to start monitoring it:

```bash
cronwatch --name "daily-backup" --timeout 300 -- /usr/local/bin/backup.sh
```

Register a job and set an expected maximum runtime (in seconds):

```bash
cronwatch register --name "db-cleanup" --max-duration 120 --alert-email ops@example.com
```

View the status of all monitored jobs:

```bash
cronwatch status
```

If a job exceeds its expected duration or exits with a non-zero code, `cronwatch` will log the failure and send an alert via the configured notification channel (email, Slack, or webhook).

### Configuration

cronwatch reads from `~/.cronwatch/config.toml` by default:

```toml
[alerts]
email = "ops@example.com"
slack_webhook = "https://hooks.slack.com/services/..."

[defaults]
timeout = 600
log_path = "~/.cronwatch/logs"
```

---

## Features

- Track execution time and exit codes for any cron job
- Alert via email, Slack, or custom webhook on failure or delay
- Simple TOML-based configuration
- Minimal dependencies, runs anywhere Python 3.8+ is available

---

## License

This project is licensed under the [MIT License](LICENSE).