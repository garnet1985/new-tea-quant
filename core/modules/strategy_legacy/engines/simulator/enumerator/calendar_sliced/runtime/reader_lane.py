#!/usr/bin/env python3
"""Reader Lane：长驻进程 bulk load → SlicePayload。"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

from core.modules.data_contract.contracts import ContractCacheManager
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.batch_transfer import (
    batch_to_transfer,
    estimate_transfer_payload_bytes,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.messages import (
    SHUTDOWN,
    LaneError,
    SliceLoadRequest,
    SlicePayload,
    is_shutdown,
)
from core.modules.strategy.services.data.injection.job_contract_batch import (
    StrategyJobContractBatch,
)

logger = logging.getLogger(__name__)


def reader_lane_main(
    job_payload: Dict[str, Any],
    reader_cmd_q: Any,
    payload_q: Any,
) -> None:
    """子进程入口：仅 Reader 连库。"""
    from core.modules.strategy.services.execution.worker_runtime import (
        bootstrap_strategy_worker_data_manager,
        release_strategy_worker_runtime,
    )

    bootstrap_strategy_worker_data_manager()
    contract_cache = ContractCacheManager()
    settings = StrategySettingsView.from_dict(job_payload["settings"])
    stock_ids = [
        str(s).strip() for s in (job_payload.get("stock_ids") or []) if str(s).strip()
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
                job_batch = StrategyJobContractBatch.hydrate(
                    entity_ids=stock_ids,
                    settings=settings,
                    start=req.load_start,
                    end=req.window_end,
                    contract_cache=contract_cache,
                    global_extra_cache=job_payload.get("global_extra_cache"),
                    fresh_strategy_cache=False,
                )
                transfer = batch_to_transfer(job_batch)
                payload_bytes = estimate_transfer_payload_bytes(transfer)
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
                    "[calendar_slice:reader] loaded %s (%s rows entities) in %.0fms",
                    req.slice_id,
                    len(stock_ids),
                    elapsed_ms,
                )
            except Exception as exc:
                logger.error(
                    "[calendar_slice:reader] load failed slice=%s: %s",
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
        release_strategy_worker_runtime()


__all__ = ["reader_lane_main"]
