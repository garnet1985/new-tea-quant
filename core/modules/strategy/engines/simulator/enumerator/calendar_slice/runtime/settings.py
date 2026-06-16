#!/usr/bin/env python3
"""calendar_slice 运行时调度参数（enumerator.calendar_slice）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Union

from core.modules.strategy.engines.simulator.enumerator.calendar_slice.slice_plan import (
    is_auto_setting,
)

_MAX_READER_WORKERS = 8
_MAX_QUEUE_DEPTH = 8


@dataclass(frozen=True)
class CalendarSliceRuntimeSettings:
    queue_depth: int = 1
    prefetch_enabled: bool = True
    reader_workers: int = 1
    queue_depth_raw: Union[int, str] = 1
    reader_workers_raw: Union[int, str] = 1

    @classmethod
    def from_job_payload(cls, job_payload: Dict[str, Any]) -> "CalendarSliceRuntimeSettings":
        settings = job_payload.get("settings") if isinstance(job_payload, dict) else {}
        enumerator = (settings or {}).get("enumerator") if isinstance(settings, dict) else {}
        block = (enumerator or {}).get("calendar_slice") if isinstance(enumerator, dict) else {}
        if not isinstance(block, dict):
            block = {}
        raw_depth = block.get("queue_depth", "auto")
        raw_workers = block.get("reader_workers", "auto")
        prefetch = bool(block.get("prefetch_enabled", True))

        if not prefetch:
            return cls(
                queue_depth=1,
                prefetch_enabled=False,
                reader_workers=1,
                queue_depth_raw=raw_depth,
                reader_workers_raw=raw_workers,
            )

        if is_auto_setting(raw_depth):
            depth = _MAX_QUEUE_DEPTH
        else:
            try:
                depth = int(raw_depth)
            except (TypeError, ValueError):
                depth = 1
            depth = max(1, min(_MAX_QUEUE_DEPTH, depth))

        if is_auto_setting(raw_workers):
            workers = _MAX_READER_WORKERS
        else:
            try:
                workers = int(raw_workers)
            except (TypeError, ValueError):
                workers = 1
            workers = max(1, min(_MAX_READER_WORKERS, workers))

        if not is_auto_setting(raw_depth) and not is_auto_setting(raw_workers):
            if workers > 1:
                depth = max(depth, min(workers, _MAX_QUEUE_DEPTH))

        return cls(
            queue_depth=depth,
            prefetch_enabled=True,
            reader_workers=workers,
            queue_depth_raw=raw_depth,
            reader_workers_raw=raw_workers,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "queue_depth": self.queue_depth_raw,
            "prefetch_enabled": self.prefetch_enabled,
            "reader_workers": self.reader_workers_raw,
        }


__all__ = ["CalendarSliceRuntimeSettings", "is_auto_setting"]
