#!/usr/bin/env python3
"""Tag calendar_slice 编排：Reader ∥ Compute + Runtime Planner。"""

from __future__ import annotations

import logging
import multiprocessing as mp
import time
from typing import Any, Dict, List, Optional, Sequence

from core.infra.job_pipeline.profile import WorkerProfiles
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.memory_monitor import (
    collect_child_pids,
    job_tree_rss_mb,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.messages import (
    SHUTDOWN,
    FinalizeDone,
    LaneError,
    SliceDone,
    SliceLoadRequest,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.payload_relay import (
    PayloadRelayThread,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.planner import (
    build_runtime_plan,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.runtime_plan import (
    CalendarSliceRuntimePlan,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.settings import (
    CalendarSliceRuntimeSettings,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.slice_plan import (
    plan_calendar_slices,
)
from core.modules.tag.engines.sliced.runtime.compute_lane import (
    compute_lane_main,
    resolve_open_dates_for_job,
)
from core.modules.tag.engines.sliced.load_range import tag_slice_load_start
from core.modules.tag.engines.sliced.runtime.reader_lane import reader_lane_main

logger = logging.getLogger(__name__)


class TagCalendarSliceOrchestrator:
    """JobPipeline 子进程内：spawn Reader + Compute，Runtime Planner 调度 preload。"""

    def __init__(self, job_payload: Dict[str, Any]):
        self.job_payload = job_payload
        self.entity_ids = list(job_payload.get("entity_ids") or [])
        self.runtime_settings = CalendarSliceRuntimeSettings.from_worker_profile(
            WorkerProfiles.TAG
        )
        self._plan: Optional[CalendarSliceRuntimePlan] = None

    def run(self) -> Dict[str, Any]:
        open_dates = resolve_open_dates_for_job(self.job_payload)
        if not open_dates:
            return self._finish_bulk(success=True, tag_values=[])

        plan = build_runtime_plan(
            self.job_payload,
            open_days_total=len(open_dates),
            settings=self.runtime_settings,
            worker_profile=WorkerProfiles.TAG,
        )
        self._plan = plan
        self.job_payload["slice_open_days"] = plan.slice_open_days
        slices = plan_calendar_slices(open_dates, plan.slice_open_days)
        if not slices:
            return self._finish_bulk(success=True, tag_values=[])

        plan.baseline_rss_mb = job_tree_rss_mb(child_pids=())

        ctx = mp.get_context("spawn")
        reader_cmd_q = ProjectContext.Queue()
        payload_q = ProjectContext.Queue(maxsize=plan.queue_capacity)
        done_q = ProjectContext.Queue()
        reader_out_q = ProjectContext.Queue() if plan.reader_workers > 1 else None
        reader_payload_q = reader_out_q if reader_out_q is not None else payload_q

        logger.info(
            "[tag:calendar_slice] plan slice_open_days=%s readers=%s preload=%s/%s queue_cap=%s",
            plan.slice_open_days,
            plan.reader_workers,
            plan.current_preload_depth,
            plan.ideal_preload_ceiling,
            plan.queue_capacity,
        )

        reader_procs: List[Any] = []
        for worker_idx in range(plan.reader_workers):
            proc = ProjectContext.Process(
                target=reader_lane_main,
                args=(self.job_payload, reader_cmd_q, reader_payload_q),
                name=f"tag_calendar_slice_reader_{worker_idx}",
                daemon=True,
            )
            reader_procs.append(proc)

        compute_proc = ProjectContext.Process(
            target=compute_lane_main,
            args=(self.job_payload, payload_q, done_q),
            name="tag_calendar_slice_compute",
            daemon=True,
        )

        relay: Optional[PayloadRelayThread] = None
        if reader_out_q is not None:
            relay = PayloadRelayThread(
                reader_out_q=reader_out_q,
                payload_q=payload_q,
                slice_count=len(slices),
            )
            relay.start()

        for proc in reader_procs:
            proc.start()
        compute_proc.start()
        child_pids = collect_child_pids([*reader_procs, compute_proc])
        try:
            return self._drive_slices(
                slices=slices,
                plan=plan,
                reader_cmd_q=reader_cmd_q,
                payload_q=payload_q,
                done_q=done_q,
                relay=relay,
                child_pids=child_pids,
            )
        except Exception as exc:
            logger.error("tag calendar_slice orchestrator failed: %s", exc, exc_info=True)
            return {
                "success": False,
                "bulk": True,
                "tag_values": [],
                "entity_count": len(self.entity_ids),
                "error": str(exc),
            }
        finally:
            if relay is not None:
                relay.stop()
                relay.join(timeout=30.0)
            self._shutdown_lanes(
                reader_cmd_q,
                payload_q,
                reader_procs,
                compute_proc,
                reader_workers=plan.reader_workers,
            )

    def _drive_slices(
        self,
        *,
        slices: List[Any],
        plan: CalendarSliceRuntimePlan,
        reader_cmd_q: Any,
        payload_q: Any,
        done_q: Any,
        relay: Optional[PayloadRelayThread],
        child_pids: Sequence[int],
    ) -> Dict[str, Any]:
        n = len(slices)
        loads_dispatched = 0

        def _dispatch_load(index: int) -> None:
            slice_desc = slices[index]
            load_start = tag_slice_load_start(slice_desc.window_start, self.job_payload)
            reader_cmd_q.put(
                SliceLoadRequest.from_descriptor(slice_desc, load_start=load_start)
            )

        def _in_flight_loads(consumed_count: int) -> int:
            return max(0, loads_dispatched - consumed_count)

        def _seed_pipeline() -> None:
            nonlocal loads_dispatched
            while loads_dispatched < n and _in_flight_loads(0) < plan.ahead_limit:
                _dispatch_load(loads_dispatched)
                loads_dispatched += 1

        def _top_up_pipeline(consumed_count: int) -> None:
            nonlocal loads_dispatched
            while (
                loads_dispatched < n
                and _in_flight_loads(consumed_count) < plan.ahead_limit
            ):
                _dispatch_load(loads_dispatched)
                loads_dispatched += 1

        _seed_pipeline()

        for i in range(n):
            if relay is not None and relay.errors:
                raise RuntimeError(f"reader lane: {relay.errors[0].message}")

            done_msg = done_q.get()
            if isinstance(done_msg, LaneError):
                raise RuntimeError(f"{done_msg.lane} lane: {done_msg.message}")
            if not isinstance(done_msg, SliceDone):
                raise RuntimeError(f"unexpected done message: {type(done_msg)!r}")
            if done_msg.slice_index != i:
                raise RuntimeError(
                    f"slice order mismatch: expected {i}, got {done_msg.slice_index}"
                )

            rss = job_tree_rss_mb(child_pids=child_pids)
            plan.record_slice(
                slice_index=i,
                load_sec=done_msg.load_elapsed_ms / 1000.0,
                compute_sec=done_msg.compute_elapsed_ms / 1000.0,
                rss_after_mb=rss,
                payload_bytes=int(done_msg.payload_bytes or 0),
            )
            if i < 2:
                plan.refine_from_timings()
            plan.adjust_preload_after_slice(job_rss_mb=rss)
            _top_up_pipeline(i + 1)

            logger.info(
                "[tag:calendar_slice] slice %s/%s done (%s) preload=%s",
                i + 1,
                n,
                done_msg.slice_id,
                plan.current_preload_depth,
            )

        logger.info("[tag:calendar_slice] all slices done, finalizing results…")
        self._signal_shutdown(
            reader_cmd_q,
            payload_q,
            reader_workers=plan.reader_workers,
        )

        finalize = done_q.get(timeout=3600)
        if isinstance(finalize, LaneError):
            raise RuntimeError(f"{finalize.lane} lane: {finalize.message}")
        if not isinstance(finalize, FinalizeDone):
            raise RuntimeError(f"expected FinalizeDone, got {type(finalize)!r}")

        summary = {}
        if finalize.stock_results:
            summary = dict(finalize.stock_results[0] or {})
        tag_values = list(summary.get("tag_values") or [])
        perf = dict(finalize.performance_metrics or {})
        perf["calendar_slice_runtime_plan"] = plan.to_dict()

        return self._finish_bulk(
            success=bool(summary.get("success", True)),
            tag_values=tag_values,
            errors=list(summary.get("errors") or []),
            performance_metrics=perf,
        )

    @staticmethod
    def _signal_shutdown(reader_cmd_q: Any, payload_q: Any, *, reader_workers: int = 1) -> None:
        for _ in range(max(1, reader_workers)):
            try:
                reader_cmd_q.put(SHUTDOWN)
            except Exception:
                pass
        try:
            payload_q.put(SHUTDOWN)
        except Exception:
            pass

    @staticmethod
    def _shutdown_lanes(
        reader_cmd_q: Any,
        payload_q: Any,
        reader_procs: Sequence[Any],
        compute_proc: Any,
        *,
        reader_workers: int = 1,
    ) -> None:
        TagCalendarSliceOrchestrator._signal_shutdown(
            reader_cmd_q,
            payload_q,
            reader_workers=reader_workers,
        )
        for proc in reader_procs:
            if proc is None:
                continue
            proc.join(timeout=30.0)
            if proc.is_alive():
                logger.warning("[tag:calendar_slice] reader did not exit cleanly, terminating")
                proc.terminate()
                proc.join(timeout=5.0)
        if compute_proc is not None:
            compute_proc.join(timeout=30.0)
            if compute_proc.is_alive():
                logger.warning("[tag:calendar_slice] compute did not exit cleanly, terminating")
                compute_proc.terminate()
                compute_proc.join(timeout=5.0)

    def _finish_bulk(
        self,
        *,
        success: bool,
        tag_values: List[Dict[str, Any]],
        errors: Optional[List[str]] = None,
        performance_metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "success": success and not errors,
            "bulk": True,
            "tag_values": tag_values,
            "total_tags": len(tag_values),
            "entity_count": len(self.entity_ids),
            "errors": errors or [],
            "performance_metrics": performance_metrics or {},
        }


__all__ = ["TagCalendarSliceOrchestrator"]
