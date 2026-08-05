"""Slice run monitor: aggregate slice samples and memory pressure analysis."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.core.shared.types import JobReport

logger = logging.getLogger(__name__)

DEFAULT_EVALUATION_SLICE_INTERVAL = 5
DEFAULT_WARMUP_SLICES = 2
DEFAULT_MEMORY_HIGH_WATERMARK = 0.85
DEFAULT_MEMORY_LOW_WATERMARK = 0.60


@dataclass(frozen=True)
class SliceMonitorPlanSnapshot:
    """Planner fields required by the slice run monitor."""

    reader_workers: int
    queue_capacity: int
    preload_depth: int
    slice_open_days: int
    dispatch_slices: int
    reader_memory_budget_mb: float
    compute_memory_budget_mb: float
    payload_memory_budget_mb: float
    memory_budget_mb: float


@dataclass(frozen=True)
class SliceMonitorConfig:
    """Monitor evaluation window config for a slice run."""

    evaluation_slice_interval: int = DEFAULT_EVALUATION_SLICE_INTERVAL
    warmup_slices: int = DEFAULT_WARMUP_SLICES
    memory_high_watermark: float = DEFAULT_MEMORY_HIGH_WATERMARK
    memory_low_watermark: float = DEFAULT_MEMORY_LOW_WATERMARK

    @classmethod
    def from_dispatch_plan(
        cls,
        plan: SliceMonitorPlanSnapshot,
        performance: Dict[str, Any],
    ) -> SliceMonitorConfig:
        _ = plan
        return cls(
            evaluation_slice_interval=max(
                1,
                int(
                    performance.get(
                        "monitor_evaluation_slice_interval",
                        DEFAULT_EVALUATION_SLICE_INTERVAL,
                    )
                ),
            ),
            warmup_slices=max(
                0,
                int(performance.get("monitor_warmup_slices", DEFAULT_WARMUP_SLICES)),
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
        )


@dataclass
class SliceProgressSample:
    slice_index: int
    load_sec: float
    compute_sec: float
    rss_after_mb: float
    payload_mb: float
    success: bool = True


@dataclass
class SliceMonitorStats:
    completed_slices: int = 0
    evaluation_count: int = 0
    mb_per_slice_reader_hat: float = 0.0
    mb_per_slice_compute_hat: float = 0.0
    mb_per_slice_payload_hat: float = 0.0
    sec_per_slice_reader_hat: float = 0.0
    sec_per_slice_compute_hat: float = 0.0
    peak_rss_mb: float = 0.0
    baseline_rss_mb: float = 0.0
    runtime_preload_depth: Optional[int] = None
    runtime_reader_workers: Optional[int] = None
    memory_pressure_detected: bool = False
    recommended_preload_depth: Optional[int] = None
    recommended_reader_workers: Optional[int] = None
    slice_samples: List[Dict[str, Any]] = field(default_factory=list)


class SliceRunMonitor:
    """
    Runtime monitor for a calendar-slice run.

    v1: slice samples are ingested from the bulk orchestrator result (post-job).
    Aggregates window metrics and flags memory pressure vs dispatch plan.
    """

    def __init__(
        self,
        plan: SliceMonitorPlanSnapshot,
        config: SliceMonitorConfig,
        *,
        available_memory_mb: float,
    ) -> None:
        self._plan = plan
        self._config = config
        self._available_memory_mb = max(1.0, available_memory_mb)
        self._window_samples: List[SliceProgressSample] = []
        self._stats = SliceMonitorStats(
            recommended_preload_depth=plan.preload_depth,
            recommended_reader_workers=plan.reader_workers,
        )

    @property
    def stats(self) -> SliceMonitorStats:
        return self._stats

    def record(self, sample: SliceProgressSample) -> None:
        self._window_samples.append(sample)
        self._stats.completed_slices += 1
        if sample.rss_after_mb > self._stats.peak_rss_mb:
            self._stats.peak_rss_mb = sample.rss_after_mb
        self.maybe_evaluate()

    def record_from_job_report(self, report: JobReport) -> None:
        """Ingest slice samples embedded in a bulk orchestrator JobReport."""
        runtime_plan = _runtime_plan_from_report(report)
        if runtime_plan:
            self._ingest_runtime_plan(runtime_plan)

        for sample in _samples_from_job_report(report):
            self.record(sample)

    def maybe_evaluate(self) -> None:
        if len(self._window_samples) < self._config.evaluation_slice_interval:
            return
        self._evaluate_window()
        self._window_samples.clear()

    def flush(self) -> None:
        if self._window_samples:
            self._evaluate_window()
            self._window_samples.clear()
        self._finalize_recommendations()

    def _ingest_runtime_plan(self, runtime_plan: Dict[str, Any]) -> None:
        baseline = runtime_plan.get("baseline_rss_mb")
        if baseline is not None:
            self._stats.baseline_rss_mb = float(baseline)

        preload = runtime_plan.get("current_preload_depth")
        if preload is not None:
            self._stats.runtime_preload_depth = int(preload)

        readers = runtime_plan.get("reader_workers")
        if readers is not None:
            self._stats.runtime_reader_workers = int(readers)

        exported = runtime_plan.get("slice_samples")
        if isinstance(exported, list):
            self._stats.slice_samples = [dict(item) for item in exported if isinstance(item, dict)]

    def _evaluate_window(self) -> None:
        if not self._window_samples:
            return

        if self._stats.completed_slices <= self._config.warmup_slices:
            self._aggregate_metrics(log_only=True)
            return

        self._aggregate_metrics(log_only=False)
        self._stats.evaluation_count += 1
        self._apply_memory_policy()

    def _aggregate_metrics(self, *, log_only: bool) -> None:
        samples = self._window_samples
        if not samples:
            return

        payload_mbs = [s.payload_mb for s in samples if s.payload_mb > 0.0]
        loads = [s.load_sec for s in samples if s.load_sec > 0.0]
        computes = [s.compute_sec for s in samples if s.compute_sec > 0.0]
        baseline = self._stats.baseline_rss_mb
        rss_deltas = [
            max(s.rss_after_mb - baseline, 0.0)
            for s in samples
            if s.rss_after_mb > 0.0
        ]

        if payload_mbs:
            self._stats.mb_per_slice_payload_hat = _median(payload_mbs)
        if loads:
            self._stats.sec_per_slice_reader_hat = sum(loads) / len(loads)
        if computes:
            self._stats.sec_per_slice_compute_hat = sum(computes) / len(computes)

        if rss_deltas:
            delta = _median(rss_deltas)
            io_share = self._stats.sec_per_slice_reader_hat / max(
                self._stats.sec_per_slice_reader_hat + self._stats.sec_per_slice_compute_hat,
                0.001,
            )
            self._stats.mb_per_slice_reader_hat = max(0.1, delta * io_share)
            self._stats.mb_per_slice_compute_hat = max(0.1, delta * (1.0 - io_share))
        elif payload_mbs:
            self._stats.mb_per_slice_payload_hat = _median(payload_mbs)

        logger.debug(
            "Slice monitor window: slices=%s payload=%.1fMB io=%.3fs compute=%.3fs%s",
            len(samples),
            self._stats.mb_per_slice_payload_hat,
            self._stats.sec_per_slice_reader_hat,
            self._stats.sec_per_slice_compute_hat,
            " (warmup/log only)" if log_only else "",
        )

    def _apply_memory_policy(self) -> None:
        plan = self._plan
        preload = self._stats.runtime_preload_depth or plan.preload_depth
        readers = self._stats.runtime_reader_workers or plan.reader_workers

        mb_reader = max(
            0.1,
            self._stats.mb_per_slice_reader_hat
            or plan.reader_memory_budget_mb / max(preload, 1),
        )
        mb_compute = max(0.1, self._stats.mb_per_slice_compute_hat or plan.compute_memory_budget_mb)
        mb_payload = max(
            0.1,
            self._stats.mb_per_slice_payload_hat
            or plan.payload_memory_budget_mb / max(plan.queue_capacity, 1),
        )
        mb_per_slice = max(1.0, mb_reader + mb_payload)

        from core.modules.backtest_engine.core.schedule.slice_based.slice_width import (
            SliceMemoryPlanner,
        )

        # Width stays fixed; only the reader queue (preload_depth) adapts.
        recommended = SliceMemoryPlanner.refine_queue_depth(
            budget_mb=self._available_memory_mb,
            mb_per_slice=mb_per_slice,
            reader_workers=readers,
            current_queue=preload,
            t_load_sec=self._stats.sec_per_slice_reader_hat or None,
            t_compute_sec=self._stats.sec_per_slice_compute_hat or None,
        )
        self._stats.recommended_preload_depth = recommended
        self._stats.recommended_reader_workers = readers

        resident = (
            SliceMemoryPlanner.in_flight(
                queue_depth=preload, reader_workers=readers
            )
            * mb_per_slice
            + mb_compute
        )
        high = self._available_memory_mb * self._config.memory_high_watermark
        if resident > high or recommended < preload:
            self._stats.memory_pressure_detected = True
            logger.info(
                "Slice monitor: adjust preload_depth %s→%s "
                "(resident≈%.0fMB high=%.0fMB; slice_open_days fixed=%s, readers=%s)",
                preload,
                recommended,
                resident,
                high,
                plan.slice_open_days,
                readers,
            )

    def _finalize_recommendations(self) -> None:
        if self._stats.recommended_preload_depth is None:
            self._stats.recommended_preload_depth = (
                self._stats.runtime_preload_depth or self._plan.preload_depth
            )
        if self._stats.recommended_reader_workers is None:
            self._stats.recommended_reader_workers = (
                self._stats.runtime_reader_workers or self._plan.reader_workers
            )


def _runtime_plan_from_report(report: JobReport) -> Dict[str, Any]:
    data = _report_data(report)
    perf = data.get("performance_metrics") or {}
    runtime_plan = perf.get("calendar_slice_runtime_plan")
    return dict(runtime_plan) if isinstance(runtime_plan, dict) else {}


def _samples_from_job_report(report: JobReport) -> List[SliceProgressSample]:
    data = _report_data(report)
    perf = data.get("performance_metrics") or {}
    runtime_plan = perf.get("calendar_slice_runtime_plan") or {}
    raw_samples = runtime_plan.get("slice_samples") or []
    samples: List[SliceProgressSample] = []
    if not isinstance(raw_samples, list):
        return samples

    for item in raw_samples:
        if not isinstance(item, dict):
            continue
        samples.append(
            SliceProgressSample(
                slice_index=int(item.get("slice_index") or len(samples)),
                load_sec=float(item.get("load_sec") or 0.0),
                compute_sec=float(item.get("compute_sec") or 0.0),
                rss_after_mb=float(item.get("rss_after_mb") or 0.0),
                payload_mb=float(item.get("payload_mb") or 0.0),
                success=bool(report.success),
            )
        )
    return samples


def _report_data(report: JobReport) -> Dict[str, Any]:
    if isinstance(report.data, dict):
        return report.data
    return {}


def _median(values: List[float]) -> float:
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


__all__ = [
    "SliceMonitorConfig",
    "SliceMonitorPlanSnapshot",
    "SliceMonitorStats",
    "SliceProgressSample",
    "SliceRunMonitor",
]
