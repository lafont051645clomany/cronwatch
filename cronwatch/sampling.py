"""Run sampling: randomly sample a fraction of job runs for lightweight analysis."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from cronwatch.tracker import JobRun


@dataclass
class SamplingConfig:
    """Configuration for run sampling."""
    rate: float = 1.0          # fraction [0.0, 1.0] of runs to keep
    seed: Optional[int] = None # optional RNG seed for reproducibility
    min_samples: int = 1       # always keep at least this many runs

    def __post_init__(self) -> None:
        if not (0.0 <= self.rate <= 1.0):
            raise ValueError(f"rate must be in [0.0, 1.0], got {self.rate}")
        if self.min_samples < 0:
            raise ValueError("min_samples must be >= 0")


@dataclass
class SampleResult:
    """Outcome of a sampling operation."""
    sampled: List[JobRun]
    total: int
    dropped: int

    @property
    def kept(self) -> int:
        return len(self.sampled)

    @property
    def effective_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.kept / self.total


def sample_runs(
    runs: Sequence[JobRun],
    cfg: SamplingConfig,
    *,
    rng: Optional[random.Random] = None,
) -> SampleResult:
    """Return a sampled subset of *runs* according to *cfg*.

    When ``cfg.rate`` is 1.0 all runs are returned unchanged.  For smaller
    rates each run is included independently with probability ``cfg.rate``
    subject to the ``min_samples`` floor.
    """
    if rng is None:
        rng = random.Random(cfg.seed)

    total = len(runs)

    if cfg.rate >= 1.0:
        return SampleResult(sampled=list(runs), total=total, dropped=0)

    if total == 0:
        return SampleResult(sampled=[], total=0, dropped=0)

    selected: List[JobRun] = [r for r in runs if rng.random() < cfg.rate]

    # Enforce min_samples floor by drawing from the remainder if needed.
    if len(selected) < cfg.min_samples:
        pool = [r for r in runs if r not in selected]
        needed = min(cfg.min_samples - len(selected), len(pool))
        selected.extend(rng.sample(pool, needed))

    return SampleResult(
        sampled=selected,
        total=total,
        dropped=total - len(selected),
    )


def filter_by_sample(
    runs: Sequence[JobRun],
    rate: float,
    seed: Optional[int] = None,
) -> List[JobRun]:
    """Convenience wrapper — returns only the sampled runs list."""
    cfg = SamplingConfig(rate=rate, seed=seed)
    return sample_runs(runs, cfg).sampled
