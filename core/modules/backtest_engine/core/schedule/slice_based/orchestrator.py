"""BE-owned slice schedule: windows, reader/queue, progress, queue refine.

Strategy only receives ready ``entity_contracts`` on ``job_context.init`` and
runs business ticks — it does not drive load / prefetch / queue depth.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.modules.backtest_engine.core.schedule.slice_based.reader_pool import (
    SliceReaderPool,
)
from core.modules.backtest_engine.core.schedule.slice_based.slice_width import (
    SliceMemoryPlanner,
)
from core.modules.backtest_engine.core.shared.progress import RunProgressReporter
from core.modules.backtest_engine.core.shared.types import JobContext, RunCallbacks
from core.modules.backtest_engine.core.timeline.timeline import Timeline

logger = logging.getLogger(__name__)


@dataclass
class SliceScheduleState:
    """Scheduling state for one slice_based job (BE-owned, not Strategy)."""

    points: List[str]
    slice_open_days: int
    min_required: int
    head_sample_slices: int
    memory_budget_mb: float
    reader_pool: SliceReaderPool
    baseline_rss_mb: float = 0.0
    slice_index: int = 0
    per_entity_load_count: int = 0
    slice_samples: List[Dict[str, Any]] = field(default_factory=list)
    window_t0: float = 0.0
    window_load_sec: float = 0.0
    queue_refined: bool = False


class SliceOrchestrator:
    """Drive formal slice windows: load → tick business days → progress → refine."""

    @classmethod
    def run(cls, job_context: JobContext, *, callbacks: RunCallbacks) -> Dict[str, Any]:
        timeline = Timeline.read_for_job(job_context.payload)
        if timeline is None:
            raise ValueError(
                "未找到引擎 timeline：请在探针前 run(start=, end=) / Timeline.set"
            )
        clipped = timeline.clipped()
        points = list(clipped.points or ())
        plan = cls._plan_dict(job_context)
        pool = cls._reader_pool(job_context, plan)
        sched = SliceScheduleState(
            points=points,
            slice_open_days=max(1, int(plan.get("slice_open_days") or 20)),
            min_required=SliceMemoryPlanner.default_min_required(
                plan.get("min_required_records")
                or (job_context.payload or {}).get("min_required_records")
            ),
            head_sample_slices=max(
                0, int((job_context.payload or {}).get("_slice_head_sample_slices") or 0)
            ),
            memory_budget_mb=float(plan.get("memory_budget_mb") or 0.0),
            reader_pool=pool,
            baseline_rss_mb=0.0,
        )

        init = job_context.init if isinstance(job_context.init, dict) else {}
        job_context.init = init
        init.setdefault("entity_contracts", {})
        init.setdefault("global_data", {})

        result: Dict[str, Any] = {"success": True}

        if not points:
            logger.warning("SliceOrchestrator: timeline 无 points")
            return cls._finish(job_context, clipped, sched, result)

        RunProgressReporter.report_from_payload(job_context.payload, 0)
        windows = cls.split_windows(len(points), sched.slice_open_days)
        on_tick = callbacks.on_tick
        on_task_start = callbacks.on_task_start
        on_task_complete = callbacks.on_task_complete
        task_total = len(windows)

        # Run-scoped prep (globals/state) before RSS baseline — same footing as
        # legacy job-level on_task_start, so payload_mb = rss - baseline excludes
        # globals. Per-slice on_task_start below may no-op once state exists.
        if on_task_start is not None:
            started = on_task_start(job_context)
            if started is not None:
                job_context.init = started
        sched.baseline_rss_mb = cls._process_rss_mb()

        for slice_index, (start_idx, end_idx) in enumerate(windows):
            # One Task = one formal slice compute.
            sched.slice_index = slice_index
            sched.window_t0 = time.perf_counter()
            sched.window_load_sec = 0.0
            cls._load_window(job_context, sched, start_idx, end_idx)
            cls._prefetch_ahead(job_context, sched, after_end_idx=end_idx)

            if on_task_start is not None:
                started = on_task_start(job_context)
                if started is not None:
                    job_context.init = started

            for index in range(start_idx, end_idx + 1):
                point = points[index]
                if on_tick is not None:
                    on_tick(job_context, point, index)

            task_init = job_context.init if isinstance(job_context.init, dict) else {}
            job_context.init = task_init
            task_init["_task_index"] = slice_index + 1
            task_init["_task_total"] = task_total

            if on_task_complete is not None:
                extra = on_task_complete(job_context)
                if isinstance(extra, dict):
                    result = {**result, **extra}

            cls._complete_window(job_context, sched, end_idx)

        return cls._finish(job_context, clipped, sched, result)

    @classmethod
    def split_windows(
        cls, point_count: int, slice_open_days: int
    ) -> List[Tuple[int, int]]:
        """Return inclusive ``(start_idx, end_idx)`` windows over ``[0, point_count)``."""
        if point_count <= 0:
            return []
        width = max(1, int(slice_open_days))
        windows: List[Tuple[int, int]] = []
        start = 0
        while start < point_count:
            end = min(start + width - 1, point_count - 1)
            windows.append((start, end))
            start = end + 1
        return windows

    @classmethod
    def lookback_start_index(cls, window_start_idx: int, min_required: int) -> int:
        need = max(1, int(min_required))
        return max(0, int(window_start_idx) - need + 1)

    @classmethod
    def _load_window(
        cls,
        job_context: JobContext,
        sched: SliceScheduleState,
        start_idx: int,
        end_idx: int,
    ) -> None:
        load_start = cls.lookback_start_index(start_idx, sched.min_required)
        start = sched.points[load_start]
        end = sched.points[end_idx]
        t0 = time.perf_counter()
        contracts = sched.reader_pool.load_window(
            job_context.payload or {},
            start=start,
            end=end,
            perf=None,
        )
        load_sec = max(0.0, time.perf_counter() - t0)
        sched.window_load_sec += load_sec
        sched.per_entity_load_count += 1
        init = job_context.init
        assert isinstance(init, dict)
        init["entity_contracts"] = contracts
        logger.info(
            "slice window load: slice=%s idx=%s..%s load_idx=%s..%s "
            "dates=%s..%s load_sec=%.3f loads=%s queue_ready=%s readers_loading=%s",
            sched.slice_index,
            start_idx,
            end_idx,
            load_start,
            end_idx,
            start,
            end,
            load_sec,
            sched.per_entity_load_count,
            sched.reader_pool.ready_count(),
            sched.reader_pool.loading_count(),
        )

    @classmethod
    def _prefetch_ahead(
        cls,
        job_context: JobContext,
        sched: SliceScheduleState,
        *,
        after_end_idx: int,
    ) -> None:
        pool = sched.reader_pool
        if pool.reader_workers <= 0 or pool.queue_depth <= 0:
            return
        last = len(sched.points) - 1
        cursor = max(0, int(after_end_idx) + 1)
        submitted = 0
        while cursor <= last and submitted < pool.queue_depth:
            nwe = min(cursor + sched.slice_open_days - 1, last)
            load_start = cls.lookback_start_index(cursor, sched.min_required)
            ok = pool.prefetch(
                job_context.payload or {},
                start=sched.points[load_start],
                end=sched.points[nwe],
            )
            if not ok:
                break
            submitted += 1
            cursor = nwe + 1

    @classmethod
    def _complete_window(
        cls,
        job_context: JobContext,
        sched: SliceScheduleState,
        end_idx: int,
    ) -> None:
        if (
            sched.head_sample_slices > 0
            and len(sched.slice_samples) < sched.head_sample_slices
        ):
            wall = max(0.0, time.perf_counter() - sched.window_t0)
            load_sec = round(max(0.0, sched.window_load_sec), 4)
            compute_sec = round(max(0.0, wall - load_sec), 4)
            rss = cls._process_rss_mb()
            sched.slice_samples.append(
                {
                    "slice_index": len(sched.slice_samples),
                    "load_sec": load_sec,
                    "compute_sec": compute_sec,
                    "serialize_sec": 0.0,
                    "deserialize_sec": 0.0,
                    "rss_after_mb": round(rss, 1),
                    "payload_mb": round(max(0.0, rss - sched.baseline_rss_mb), 1),
                    "payload_bytes": int(
                        max(0.0, rss - sched.baseline_rss_mb) * 1024 * 1024
                    ),
                }
            )
            cls._maybe_refine_queue(job_context, sched)

        # Release per-entity contracts; next window loads fresh.
        init = job_context.init
        if isinstance(init, dict):
            init["entity_contracts"] = {}

        completed = sched.slice_index + 1
        RunProgressReporter.report_from_payload(job_context.payload, completed)
        if end_idx + 1 < len(sched.points):
            cls._prefetch_ahead(job_context, sched, after_end_idx=end_idx)

    @classmethod
    def _maybe_refine_queue(
        cls, job_context: JobContext, sched: SliceScheduleState
    ) -> None:
        if sched.queue_refined:
            return
        if len(sched.slice_samples) != sched.head_sample_slices:
            return
        if sched.memory_budget_mb <= 0:
            return
        new_n = SliceReaderPool.refine_queue_from_samples(
            sched.reader_pool,
            sched.slice_samples,
            budget_mb=sched.memory_budget_mb,
        )
        sched.queue_refined = True
        plan = cls._plan_dict(job_context)
        plan["preload_depth"] = new_n
        plan["queue_capacity"] = new_n
        plan["queue_depth"] = new_n
        if isinstance(job_context.payload, dict):
            job_context.payload["_slice_plan"] = plan
        logger.info(
            "slice queue refine after %s head samples → queue=%s",
            sched.head_sample_slices,
            new_n,
        )

    @classmethod
    def _finish(
        cls,
        job_context: JobContext,
        timeline: Timeline,
        sched: SliceScheduleState,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        metrics = result.get("performance_metrics")
        if not isinstance(metrics, dict):
            metrics = {}
            result["performance_metrics"] = metrics
        metrics["calendar_slice_runtime_plan"] = {
            "baseline_rss_mb": float(sched.baseline_rss_mb or 0.0),
            "slice_samples": list(sched.slice_samples),
            "per_entity_load_count": int(sched.per_entity_load_count),
            "formal_slices_completed": int(sched.slice_index + 1)
            if sched.points
            else 0,
            "reader_workers": int(sched.reader_pool.reader_workers),
            "queue_depth": int(sched.reader_pool.queue_depth),
        }
        return result

    @classmethod
    def _plan_dict(cls, job_context: JobContext) -> Dict[str, Any]:
        raw = (job_context.payload or {}).get("_slice_plan") or {}
        return dict(raw) if isinstance(raw, dict) else {}

    @classmethod
    def _reader_pool(
        cls, job_context: JobContext, plan: Dict[str, Any]
    ) -> SliceReaderPool:
        injected = (job_context.payload or {}).get("_slice_reader_pool")
        if isinstance(injected, SliceReaderPool):
            return injected
        return SliceReaderPool(
            reader_workers=int(plan.get("reader_workers") or 0),
            queue_depth=int(
                plan.get("preload_depth") or plan.get("queue_capacity") or 0
            ),
            load_per_entity_window=(job_context.payload or {}).get(
                "_load_per_entity_window"
            ),
        )

    @staticmethod
    def _process_rss_mb() -> float:
        try:
            import os

            import psutil

            return float(psutil.Process(os.getpid()).memory_info().rss) / (
                1024.0 * 1024.0
            )
        except Exception:
            return 0.0


class SliceWorkerExecute:
    """Slice-mode execute_fn: BE orchestrator + Strategy callbacks."""

    def __init__(self, callbacks: Optional[RunCallbacks] = None) -> None:
        from core.modules.backtest_engine.core.shared.types import RunCallbacks as RC

        self.callbacks = callbacks or RC()

    def __call__(self, job_context: JobContext) -> Dict[str, Any]:
        return SliceOrchestrator.run(job_context, callbacks=self.callbacks)


__all__ = [
    "SliceOrchestrator",
    "SliceScheduleState",
    "SliceWorkerExecute",
]
