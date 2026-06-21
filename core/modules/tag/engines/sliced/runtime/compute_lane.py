#!/usr/bin/env python3
"""Tag Compute Lane：长驻进程消费 SlicePayload（无 DB）。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.strategy.engines.shared.helpers.backtest_calendar_context import (
    BacktestCalendarContext,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.messages import (
    SHUTDOWN,
    FinalizeDone,
    LaneError,
    SliceDone,
    SlicePayload,
    is_shutdown,
)
from core.modules.tag.engines.sliced.runtime.compute_engine import TagSliceComputeEngine

logger = logging.getLogger(__name__)


def compute_lane_main(
    job_payload: Dict[str, Any],
    payload_q: Any,
    done_q: Any,
) -> None:
    engine = TagSliceComputeEngine(job_payload)
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
            started = __import__("time").perf_counter()
            engine.run_slice(payload)
            compute_ms = (__import__("time").perf_counter() - started) * 1000.0
            done_q.put(
                SliceDone(
                    slice_index=payload.slice_index,
                    slice_id=payload.slice_id,
                    load_elapsed_ms=float(payload.load_elapsed_ms),
                    compute_elapsed_ms=float(compute_ms),
                    payload_bytes=int(payload.payload_bytes or 0),
                )
            )
            logger.debug(
                "[tag:calendar_slice:compute] finished %s index=%s",
                payload.slice_id,
                payload.slice_index,
            )
    except Exception as exc:
        logger.error("[tag:calendar_slice:compute] failed: %s", exc, exc_info=True)
        done_q.put(LaneError(lane="compute", message=str(exc)))
        return

    try:
        logger.info("[tag:calendar_slice:compute] finalizing tag results…")
        summary = engine.finalize_all()
        done_q.put(
            FinalizeDone(
                stock_results=[summary],
                performance_metrics={"tag_slice_summary": summary},
            )
        )
    except Exception as exc:
        logger.error("[tag:calendar_slice:compute] finalize failed: %s", exc, exc_info=True)
        done_q.put(LaneError(lane="compute", message=str(exc)))


def resolve_open_dates_for_job(job_payload: Dict[str, Any]) -> List[str]:
    cal = BacktestCalendarContext.from_dict(job_payload.get("backtest_calendar"))
    if cal is None:
        return []
    start = str(job_payload.get("start_date") or "")
    end = str(job_payload.get("end_date") or "")
    return [d for d in cal.open_dates if start <= d <= end]


__all__ = ["compute_lane_main", "resolve_open_dates_for_job"]
