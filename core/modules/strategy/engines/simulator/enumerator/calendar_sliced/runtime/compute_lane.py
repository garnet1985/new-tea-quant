#!/usr/bin/env python3
"""Compute Lane：长驻进程消费 SlicePayload（无 DB）。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.strategy.engines.shared.helpers.backtest_calendar_context import (
    BacktestCalendarContext,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.compute_engine import (
    CalendarSliceComputeEngine,
    warmup_indicator_runtime_once,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.messages import (
    SHUTDOWN,
    FinalizeDone,
    LaneError,
    SliceDone,
    SlicePayload,
    is_shutdown,
)

logger = logging.getLogger(__name__)


def compute_lane_main(
    job_payload: Dict[str, Any],
    payload_q: Any,
    done_q: Any,
    *,
    run_started_at: float,
    open_dates: List[str],
) -> None:
    """子进程入口：不 bootstrap DataManager。"""
    warmup_indicator_runtime_once()
    engine = CalendarSliceComputeEngine(job_payload)
    reporter = engine.create_progress_reporter(open_dates, run_started_at=run_started_at)
    if reporter is not None:
        reporter.seed()
    carry: Dict[str, Any] = {}
    try:
        while True:
            msg = payload_q.get()
            if is_shutdown(msg):
                break
            if isinstance(msg, LaneError):
                done_q.put(msg)
                break
            if not isinstance(msg, SlicePayload):
                continue
            payload = msg
            engine.profiler.start_timer("compute_slice")
            carry = engine.run_slice(payload, carry, reporter=reporter)
            compute_sec = engine.profiler.end_timer("compute_slice")
            done_q.put(
                SliceDone(
                    slice_index=payload.slice_index,
                    slice_id=payload.slice_id,
                    load_elapsed_ms=float(payload.load_elapsed_ms),
                    compute_elapsed_ms=float(compute_sec) * 1000.0,
                    payload_bytes=int(payload.payload_bytes or 0),
                )
            )
            logger.debug(
                "[calendar_slice:compute] finished %s index=%s",
                payload.slice_id,
                payload.slice_index,
            )
    except Exception as exc:
        logger.error("[calendar_slice:compute] failed: %s", exc, exc_info=True)
        done_q.put(LaneError(lane="compute", message=str(exc)))
        return

    try:
        engine.profiler.start_timer("total")
        logger.info("[calendar_slice:compute] finalizing stock results…")
        stock_results = engine.finalize_all()
        engine.profiler.metrics.time_total = engine.profiler.end_timer("total")
        calendar_progress = reporter.finish() if reporter is not None else {}
        done_q.put(
            FinalizeDone(
                stock_results=stock_results,
                calendar_progress=calendar_progress,
                performance_metrics=engine.profiler.finalize().to_dict(),
            )
        )
    except Exception as exc:
        logger.error("[calendar_slice:compute] finalize failed: %s", exc, exc_info=True)
        done_q.put(LaneError(lane="compute", message=str(exc)))


def resolve_open_dates_for_job(job_payload: Dict[str, Any]) -> List[str]:
    cal = BacktestCalendarContext.from_dict(job_payload.get("backtest_calendar"))
    if cal is None:
        return []
    start = str(job_payload.get("start_date") or "")
    end = str(job_payload.get("end_date") or "")
    return [d for d in cal.open_dates if start <= d <= end]


__all__ = ["compute_lane_main", "resolve_open_dates_for_job"]
