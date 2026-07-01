#!/usr/bin/env python3
"""多 Reader 并行 load 时，按 slice_index 顺序转发 SlicePayload。"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Any, List, Optional

from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.messages import (
    LaneError,
    SlicePayload,
    is_shutdown,
)

logger = logging.getLogger(__name__)


def relay_payloads_in_order(
    *,
    reader_out_q: Any,
    payload_q: Any,
    slice_count: int,
    stop_event: threading.Event,
    errors: List[LaneError],
) -> None:
    """从 reader_out_q 收集乱序 payload，按 slice_index 顺序写入 payload_q。"""
    buffer: dict[int, SlicePayload] = {}
    next_index = 0
    while next_index < slice_count:
        if stop_event.is_set() and reader_out_q.empty() and next_index not in buffer:
            pending = sorted(k for k in buffer if k >= next_index)
            if not pending:
                break
        try:
            msg = reader_out_q.get(timeout=0.25)
        except queue.Empty:
            continue
        if is_shutdown(msg):
            continue
        if isinstance(msg, LaneError):
            errors.append(msg)
            payload_q.put(msg)
            return
        if not isinstance(msg, SlicePayload):
            continue
        buffer[msg.slice_index] = msg
        while next_index in buffer:
            payload_q.put(buffer.pop(next_index))
            next_index += 1
    if next_index < slice_count:
        logger.warning(
            "[calendar_slice] payload relay stopped early: forwarded %s/%s slices",
            next_index,
            slice_count,
        )


class PayloadRelayThread:
    """后台 relay；orchestrator 在 shutdown 时 stop() 并 join。"""

    def __init__(
        self,
        *,
        reader_out_q: Any,
        payload_q: Any,
        slice_count: int,
    ) -> None:
        self._reader_out_q = reader_out_q
        self._payload_q = payload_q
        self._slice_count = slice_count
        self._stop_event = threading.Event()
        self._errors: List[LaneError] = []
        self._thread = threading.Thread(
            target=relay_payloads_in_order,
            kwargs={
                "reader_out_q": reader_out_q,
                "payload_q": payload_q,
                "slice_count": slice_count,
                "stop_event": self._stop_event,
                "errors": self._errors,
            },
            name="calendar_slice_payload_relay",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def join(self, timeout: Optional[float] = 30.0) -> None:
        self._thread.join(timeout=timeout)

    @property
    def errors(self) -> List[LaneError]:
        return self._errors


__all__ = ["PayloadRelayThread", "relay_payloads_in_order"]
