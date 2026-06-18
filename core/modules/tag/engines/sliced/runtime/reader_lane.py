#!/usr/bin/env python3
"""Tag Reader Lane：bulk stage_entities_batch → SlicePayload。"""

from __future__ import annotations

import logging
import sys
import time
from typing import Any, Dict, List

from core.modules.tag.engines.shared.staging.batch_stage import stage_entities_batch
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.messages import (
    SHUTDOWN,
    LaneError,
    SliceLoadRequest,
    SlicePayload,
    is_shutdown,
)

logger = logging.getLogger(__name__)


def _estimate_payload_bytes(transfer: Dict[str, Any]) -> int:
    try:
        return sys.getsizeof(transfer)
    except Exception:
        return 0


def reader_lane_main(
    job_payload: Dict[str, Any],
    reader_cmd_q: Any,
    payload_q: Any,
) -> None:
    from core.modules.tag.engines.shared.staging.worker_runtime import (
        create_worker_data_manager,
        release_worker_runtime,
    )

    data_mgr = create_worker_data_manager()
    entities: List[Dict[str, Any]] = list(job_payload.get("entities") or [])
    settings = dict(job_payload.get("settings") or {})
    tag_definition_ids = [
        int(t["id"])
        for t in (job_payload.get("tag_definitions") or [])
        if isinstance(t, dict) and t.get("id") is not None
    ]
    try:
        while True:
            cmd = reader_cmd_q.get()
            if is_shutdown(cmd):
                break
            if not isinstance(cmd, SliceLoadRequest):
                continue
            req = cmd
            started = time.perf_counter()
            try:
                slice_entities = [
                    {
                        **ent,
                        "start_date": req.load_start,
                        "end_date": req.window_end,
                    }
                    for ent in entities
                ]
                by_entity = stage_entities_batch(
                    data_mgr=data_mgr,
                    entities=slice_entities,
                    settings=settings,
                    tag_definition_ids=tag_definition_ids,
                )
                open_set = set(req.open_dates)
                for inject in by_entity.values():
                    trading_dates = list(inject.get("trading_dates") or [])
                    inject["trading_dates"] = [d for d in trading_dates if d in open_set]
                transfer = {"by_entity": by_entity}
                payload_bytes = _estimate_payload_bytes(transfer)
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                payload_q.put(
                    SlicePayload(
                        slice_id=req.slice_id,
                        slice_index=req.slice_index,
                        window_start=req.window_start,
                        window_end=req.window_end,
                        open_dates=req.open_dates,
                        batch_transfer=transfer,
                        load_elapsed_ms=elapsed_ms,
                        payload_bytes=payload_bytes,
                    )
                )
                logger.info(
                    "[tag:calendar_slice:reader] loaded %s (%s entities) in %.0fms",
                    req.slice_id,
                    len(by_entity),
                    elapsed_ms,
                )
            except Exception as exc:
                logger.error(
                    "[tag:calendar_slice:reader] load failed slice=%s: %s",
                    req.slice_id,
                    exc,
                    exc_info=True,
                )
                payload_q.put(
                    LaneError(
                        lane="reader",
                        message=str(exc),
                        slice_index=req.slice_index,
                    )
                )
    finally:
        release_worker_runtime()


__all__ = ["reader_lane_main"]
