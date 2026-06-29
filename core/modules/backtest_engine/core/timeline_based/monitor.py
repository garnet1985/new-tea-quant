"""Timeline run monitor: aggregate sampling and in-flight worker control."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

DEFAULT_EVALUATION_JOB_INTERVAL = 10
DEFAULT_EVALUATION_ENTITY_INTERVAL = 50
DEFAULT_WARMUP_JOBS = 3
DEFAULT_MEMORY_HIGH_WATERMARK = 0.85
DEFAULT_MEMORY_LOW_WATERMARK = 0.60


@dataclass(frozen=True)
class MonitorPlanSnapshot:
    """Planner output fields required by the run monitor."""

    entities_per_job: int
    max_workers: int
    prefetch_ahead: int
    worker_job_budget_mb: float


@dataclass(frozen=True)
class TimelineMonitorConfig:
    """Step 5 output: how often to evaluate and adjust in-flight workers."""

    evaluation_job_interval: int = DEFAULT_EVALUATION_JOB_INTERVAL
    evaluation_entity_interval: int = DEFAULT_EVALUATION_ENTITY_INTERVAL
    evaluation_requires_both: bool = False
    warmup_jobs: int = DEFAULT_WARMUP_JOBS
    memory_high_watermark: float = DEFAULT_MEMORY_HIGH_WATERMARK
    memory_low_watermark: float = DEFAULT_MEMORY_LOW_WATERMARK
    enable_raise_in_flight: bool = False  # v1: memory-only downshift; raise optional

    @classmethod
    def from_dispatch_plan(
        cls,
        plan: MonitorPlanSnapshot,
        performance: dict,
    ) -> TimelineMonitorConfig:
        return cls(
            evaluation_job_interval=max(
                1,
                int(
                    performance.get(
                        "monitor_evaluation_job_interval",
                        DEFAULT_EVALUATION_JOB_INTERVAL,
                    )
                ),
            ),
            evaluation_entity_interval=max(
                1,
                int(
                    performance.get(
                        "monitor_evaluation_entity_interval",
                        DEFAULT_EVALUATION_ENTITY_INTERVAL,
                    )
                ),
            ),
            evaluation_requires_both=bool(
                performance.get("monitor_evaluation_requires_both", False)
            ),
            warmup_jobs=max(
                0,
                int(performance.get("monitor_warmup_jobs", DEFAULT_WARMUP_JOBS)),
            ),
            memory_high_watermark=float(
                performance.get(
                    "monitor_memory_high_watermark",
                    DEFAULT_MEMORY_HIGH_WATERMARK,
                )
            ),
            memory_low_watermark=float(
                performance.get(
                    "monitor_memory_low_watermark",
                    DEFAULT_MEMORY_LOW_WATERMARK,
                )
            ),
            enable_raise_in_flight=bool(
                performance.get("monitor_enable_raise_in_flight", False)
            ),
        )


@dataclass
class TimelineJobSample:
    job_id: str
    entities_count: int
    wall_sec: float
    peak_rss_mb: Optional[float] = None
    success: bool = True


@dataclass
class TimelineMonitorStats:
    completed_jobs: int = 0
    completed_entities: int = 0
    evaluation_count: int = 0
    current_in_flight: int = 1
    mb_per_entity_hat: float = 0.0
    wall_per_entity_hat: float = 0.0
    sunk_cost_sec_hat: float = 0.0
    margin_cost_sec_per_entity_hat: float = 0.0


class TimelineRunMonitor:
    """
    Runtime monitor for a single timeline run.

    Records per-job samples; evaluates every N jobs / M entities (aggregated).
    Only adjusts current_in_flight; entities_per_job stays fixed for the run.
    """

    def __init__(
        self,
        plan: MonitorPlanSnapshot,
        config: TimelineMonitorConfig,
        *,
        available_memory_mb: float,
        cpu_workers_cap: int,
    ) -> None:
        self._plan = plan
        self._config = config
        self._available_memory_mb = max(1.0, available_memory_mb)
        self._max_in_flight_hard_cap = max(
            1,
            min(plan.max_workers, max(1, cpu_workers_cap)),
        )
        self._current_in_flight = self._max_in_flight_hard_cap
        self._window_samples: List[TimelineJobSample] = []
        self._stats = TimelineMonitorStats(
            current_in_flight=self._current_in_flight,
        )
        self._low_memory_windows = 0

    @property
    def current_in_flight(self) -> int:
        return self._current_in_flight

    @property
    def admission_limit(self) -> int:
        return self._current_in_flight + max(0, self._plan.prefetch_ahead)

    @property
    def stats(self) -> TimelineMonitorStats:
        return self._stats

    def record(self, sample: TimelineJobSample) -> None:
        self._window_samples.append(sample)
        self._stats.completed_jobs += 1
        self._stats.completed_entities += max(0, sample.entities_count)
        self.maybe_evaluate()

    def maybe_evaluate(self) -> None:
        if not self._should_evaluate():
            return
        self._evaluate_window()
        self._window_samples.clear()

    def flush(self) -> None:
        """Evaluate any remaining window samples at end of run."""
        if not self._window_samples:
            return
        self._evaluate_window()
        self._window_samples.clear()

    def _should_evaluate(self) -> bool:
        cfg = self._config
        window_jobs = len(self._window_samples)
        window_entities = sum(
            max(0, s.entities_count) for s in self._window_samples
        )
        jobs_ok = window_jobs >= cfg.evaluation_job_interval
        entities_ok = window_entities >= cfg.evaluation_entity_interval
        if cfg.evaluation_requires_both:
            return jobs_ok and entities_ok
        return jobs_ok or entities_ok

    def _evaluate_window(self) -> None:
        if not self._window_samples:
            return

        if self._stats.completed_jobs <= self._config.warmup_jobs:
            self._aggregate_metrics(log_only=True)
            return

        self._aggregate_metrics(log_only=False)
        self._stats.evaluation_count += 1
        self._apply_memory_policy()

    def _aggregate_metrics(self, *, log_only: bool) -> None:
        total_entities = sum(
            max(0, s.entities_count) for s in self._window_samples
        )
        if total_entities <= 0:
            return

        wall_sum = sum(s.wall_sec for s in self._window_samples)
        rss_samples = [
            s.peak_rss_mb
            for s in self._window_samples
            if s.peak_rss_mb is not None
        ]
        job_count = len(self._window_samples)

        margin_hat = wall_sum / total_entities
        self._stats.margin_cost_sec_per_entity_hat = margin_hat
        self._stats.wall_per_entity_hat = margin_hat

        if rss_samples:
            rss_sum = sum(rss_samples)
            self._stats.mb_per_entity_hat = rss_sum / total_entities
        else:
            self._stats.mb_per_entity_hat = self._plan.worker_job_budget_mb / max(
                1, self._plan.entities_per_job
            )

        if job_count > 0:
            avg_job_wall = wall_sum / job_count
            sunk_hat = max(0.0, avg_job_wall - margin_hat * self._plan.entities_per_job)
            self._stats.sunk_cost_sec_hat = sunk_hat

        logger.debug(
            "Monitor window: jobs=%s entities=%s mb_hat=%.3f margin=%.4fs sunk=%.3fs%s",
            job_count,
            total_entities,
            self._stats.mb_per_entity_hat,
            self._stats.margin_cost_sec_per_entity_hat,
            self._stats.sunk_cost_sec_hat,
            " (warmup/log only)" if log_only else "",
        )

    def _apply_memory_policy(self) -> None:
        epj = self._plan.entities_per_job
        mb_hat = max(0.01, self._stats.mb_per_entity_hat)
        in_flight_mb = mb_hat * epj * self._current_in_flight
        high = self._available_memory_mb * self._config.memory_high_watermark
        low = self._available_memory_mb * self._config.memory_low_watermark

        if in_flight_mb > high and self._current_in_flight > 1:
            self._current_in_flight -= 1
            self._low_memory_windows = 0
            logger.info(
                "Monitor: memory high (%.0fMB > %.0fMB), in_flight → %s",
                in_flight_mb,
                high,
                self._current_in_flight,
            )
            self._stats.current_in_flight = self._current_in_flight
            return

        if not self._config.enable_raise_in_flight:
            return

        if in_flight_mb < low and self._current_in_flight < self._max_in_flight_hard_cap:
            self._low_memory_windows += 1
            if self._low_memory_windows >= 2:
                self._current_in_flight += 1
                self._low_memory_windows = 0
                logger.info(
                    "Monitor: memory low (%.0fMB < %.0fMB), in_flight → %s",
                    in_flight_mb,
                    low,
                    self._current_in_flight,
                )
                self._stats.current_in_flight = self._current_in_flight
        else:
            self._low_memory_windows = 0
