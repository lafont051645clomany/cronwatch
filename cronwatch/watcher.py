"""High-level watcher that ties together the tracker, scheduler, and alerts."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from cronwatch.alerts import dispatch_alert
from cronwatch.config import CronwatchConfig
from cronwatch.scheduler import is_overdue
from cronwatch.tracker import JobRun, JobStatus, JobTracker

logger = logging.getLogger(__name__)


class Watcher:
    """Periodically checks all configured jobs for overdue / failed runs.

    Attributes:
        config: The loaded :class:`~cronwatch.config.CronwatchConfig`.
        tracker: The :class:`~cronwatch.tracker.JobTracker` instance.
    """

    def __init__(self, config: CronwatchConfig, tracker: Optional[JobTracker] = None) -> None:
        self.config = config
        self.tracker: JobTracker = tracker or JobTracker()
        # Track which jobs we have already alerted on to avoid spam.
        self._alerted: Dict[str, str] = {}  # job_name -> run_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_all(self) -> None:
        """Run a single pass over all configured jobs and dispatch alerts."""
        for job_cfg in self.config.jobs:
            self._check_job(job_cfg.name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_job(self, name: str) -> None:
        job_cfg = next((j for j in self.config.jobs if j.name == name), None)
        if job_cfg is None:
            logger.warning("check_job called for unknown job %r", name)
            return

        run: Optional[JobRun] = self.tracker.latest(name)

        # --- Failed run ------------------------------------------------
        if run is not None and run.status == JobStatus.FAILED:
            if self._alerted.get(name) != run.run_id:
                logger.info("Job %r failed — dispatching alert.", name)
                dispatch_alert(run, self.config.alerts)
                self._alerted[name] = run.run_id
            return

        # --- Overdue check --------------------------------------------
        last_started: Optional[datetime] = run.started_at if run else None
        if is_overdue(job_cfg, last_started):
            synthetic_id = f"{name}:overdue"
            if self._alerted.get(name) != synthetic_id:
                logger.info("Job %r is overdue — dispatching alert.", name)
                overdue_run = JobRun(
                    job_name=name,
                    run_id=synthetic_id,
                    started_at=last_started or datetime.now(timezone.utc),
                    status=JobStatus.FAILED,
                    exit_code=None,
                    error_message="Job did not start within the expected window.",
                )
                dispatch_alert(overdue_run, self.config.alerts)
                self._alerted[name] = synthetic_id
