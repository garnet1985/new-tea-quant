#!/usr/bin/env python3
"""calendar_slice v2 编排：Reader ∥ Compute + prefetch 队列。"""

from __future__ import annotations

import logging
import multiprocessing as mp
import time
from typing import Any, Dict, List, Optional, Sequence

from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.compute_lane import (
    compute_lane_main,
    resolve_open_dates_for_job,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.messages import (
    SHUTDOWN,
    FinalizeDone,
    LaneError,
    SliceDone,
    SliceLoadRequest,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.payload_relay import (
    PayloadRelayThread,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.reader_lane import (
    reader_lane_main,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.settings import (
    CalendarSliceRuntimeSettings,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_slice.slice_plan import (
    plan_calendar_slices,
)
from core.modules.strategy.engines.simulator.enumerator.worker import (
    enumeration_actual_start_date,
)

logger = logging.getLogger(__name__)


class CalendarSliceProcessOrchestrator:
    """JobPipeline 子进程内：spawn Reader + Compute，调度 prefetch。"""

    def __init__(self, job_payload: Dict[str, Any]):
        self.job_payload = job_payload
        self.stock_ids = list(job_payload.get("stock_ids") or [])
        self.start_date = str(job_payload.get("start_date") or "")
        self.end_date = str(job_payload.get("end_date") or "")
        self.slice_open_days = max(1, int(job_payload.get("slice_open_days") or 63))
        self.runtime = CalendarSliceRuntimeSettings.from_job_payload(job_payload)
        min_records = 100
        try:
            settings = job_payload.get("settings") or {}
            min_records = int((settings.get("data") or {}).get("min_required_records") or 100)
        except (TypeError, ValueError):
            pass
        self._min_required_records = max(1, min_records)

    def run(self) -> Dict[str, Any]:
        run_started_at = time.time()
        open_dates = resolve_open_dates_for_job(self.job_payload)
        slices = plan_calendar_slices(open_dates, self.slice_open_days)
        if not slices:
            return self._finish_bulk(success=True, stock_results=[])

        ctx = mp.get_context("spawn")
        reader_cmd_q = ctx.Queue()
        payload_q = ctx.Queue(maxsize=self.runtime.queue_depth)
        done_q = ctx.Queue()
        reader_out_q = ctx.Queue() if self.runtime.reader_workers > 1 else None
        reader_payload_q = reader_out_q if reader_out_q is not None else payload_q

        if self.runtime.reader_workers > 1:
            logger.info(
                "[calendar_slice] reader_workers=%s queue_depth=%s (parallel load + ordered relay)",
                self.runtime.reader_workers,
                self.runtime.queue_depth,
            )
            self._warn_multi_reader_storage()

        reader_procs: List[Any] = []
        for worker_idx in range(self.runtime.reader_workers):
            proc = ctx.Process(
                target=reader_lane_main,
                args=(self.job_payload, reader_cmd_q, reader_payload_q),
                name=f"calendar_slice_reader_{worker_idx}",
                daemon=True,
            )
            reader_procs.append(proc)

        compute_proc = ctx.Process(
            target=compute_lane_main,
            args=(
                self.job_payload,
                payload_q,
                done_q,
            ),
            kwargs={
                "run_started_at": run_started_at,
                "open_dates": open_dates,
            },
            name="calendar_slice_compute",
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
        try:
            return self._drive_slices(
                slices=slices,
                reader_cmd_q=reader_cmd_q,
                payload_q=payload_q,
                done_q=done_q,
                relay=relay,
            )
        except Exception as exc:
            logger.error("calendar_slice orchestrator failed: %s", exc, exc_info=True)
            return {
                "success": False,
                "bulk": True,
                "stock_results": [],
                "stock_ids": self.stock_ids,
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
                reader_workers=self.runtime.reader_workers,
            )

    def _drive_slices(
        self,
        *,
        slices: List[Any],
        reader_cmd_q: Any,
        payload_q: Any,
        done_q: Any,
        relay: Optional[PayloadRelayThread] = None,
    ) -> Dict[str, Any]:
        n = len(slices)
        loads_dispatched = 0
        ahead_limit = (
            self.runtime.reader_workers if self.runtime.prefetch_enabled else 1
        )

        def _dispatch_load(index: int) -> None:
            slice_desc = slices[index]
            load_start = enumeration_actual_start_date(
                slice_desc.window_start,
                self._min_required_records,
            )
            reader_cmd_q.put(
                SliceLoadRequest.from_descriptor(slice_desc, load_start=load_start)
            )

        def _seed_pipeline() -> None:
            nonlocal loads_dispatched
            while loads_dispatched < n and loads_dispatched < ahead_limit:
                _dispatch_load(loads_dispatched)
                loads_dispatched += 1

        def _top_up_pipeline(consumed_count: int) -> None:
            nonlocal loads_dispatched
            while loads_dispatched < n and loads_dispatched < consumed_count + ahead_limit:
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

            _top_up_pipeline(i + 1)

            logger.info(
                "[calendar_slice] slice %s/%s done (%s)",
                i + 1,
                n,
                done_msg.slice_id,
            )

        logger.info("[calendar_slice] all slices done, finalizing results…")
        self._signal_shutdown(
            reader_cmd_q,
            payload_q,
            reader_workers=self.runtime.reader_workers,
        )

        finalize = done_q.get(timeout=3600)
        if isinstance(finalize, LaneError):
            raise RuntimeError(f"{finalize.lane} lane: {finalize.message}")
        if not isinstance(finalize, FinalizeDone):
            raise RuntimeError(f"expected FinalizeDone, got {type(finalize)!r}")

        return self._finish_bulk(
            success=True,
            stock_results=finalize.stock_results,
            calendar_progress=finalize.calendar_progress or None,
            performance_metrics=finalize.performance_metrics or None,
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

    def _warn_multi_reader_storage(self) -> None:
        try:
            from core.modules.data_manager import DataManager

            backend = str(getattr(DataManager(is_verbose=False), "backend", "") or "").lower()
            if "duck" in backend:
                logger.warning(
                    "[calendar_slice] reader_workers=%s on DuckDB may contend on single-file "
                    "reads; prefer reader_workers=1 unless profiled",
                    self.runtime.reader_workers,
                )
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
        CalendarSliceProcessOrchestrator._signal_shutdown(
            reader_cmd_q,
            payload_q,
            reader_workers=reader_workers,
        )
        for proc in reader_procs:
            if proc is None:
                continue
            proc.join(timeout=30.0)
            if proc.is_alive():
                logger.warning("[calendar_slice] reader did not exit cleanly, terminating")
                proc.terminate()
                proc.join(timeout=5.0)
        if compute_proc is not None:
            compute_proc.join(timeout=30.0)
            if compute_proc.is_alive():
                logger.warning("[calendar_slice] compute did not exit cleanly, terminating")
                compute_proc.terminate()
                compute_proc.join(timeout=5.0)

    def _finish_bulk(
        self,
        *,
        success: bool,
        stock_results: List[Dict[str, Any]],
        calendar_progress: Optional[Dict[str, Any]] = None,
        performance_metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "success": success and all(bool(r.get("success")) for r in stock_results),
            "bulk": True,
            "stock_results": stock_results,
            "stock_ids": self.stock_ids,
            "performance_metrics": performance_metrics or {},
        }
        if calendar_progress:
            payload["calendar_progress"] = calendar_progress
        return payload


def load_stock_infos_for_ids(stock_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """主进程 enrich job：compute 子进程不连库取 meta。"""
    infos: Dict[str, Dict[str, Any]] = {}
    try:
        from core.modules.data_manager import DataManager

        dm = DataManager(is_verbose=False)
        for sid in stock_ids:
            sid = str(sid).strip()
            if not sid:
                continue
            fallback = {
                "id": sid,
                "name": sid,
                "industry": "",
                "type": "",
                "exchange_center": "",
            }
            try:
                row = dm.stock.list.load_meta(sid)
                if isinstance(row, dict) and row.get("id"):
                    infos[sid] = {**fallback, **row}
                else:
                    infos[sid] = fallback
            except Exception:
                infos[sid] = fallback
    except Exception as exc:
        logger.warning("load_stock_infos_for_ids failed: %s", exc)
        for sid in stock_ids:
            sid = str(sid).strip()
            if sid:
                infos[sid] = {"id": sid, "name": sid}
    return infos


__all__ = [
    "CalendarSliceProcessOrchestrator",
    "load_stock_infos_for_ids",
]
