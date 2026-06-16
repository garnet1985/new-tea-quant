#!/usr/bin/env python3
"""calendar_slice 运行时调度参数（enumerator.calendar_slice）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


_MAX_READER_WORKERS = 8
_MAX_QUEUE_DEPTH = 8


@dataclass(frozen=True)
class CalendarSliceRuntimeSettings:
    queue_depth: int = 1
    prefetch_enabled: bool = True
    reader_workers: int = 1

    @classmethod
    def from_job_payload(cls, job_payload: Dict[str, Any]) -> "CalendarSliceRuntimeSettings":
        settings = job_payload.get("settings") if isinstance(job_payload, dict) else {}
        enumerator = (settings or {}).get("enumerator") if isinstance(settings, dict) else {}
        block = (enumerator or {}).get("calendar_slice") if isinstance(enumerator, dict) else {}
        if not isinstance(block, dict):
            block = {}
        try:
            depth = int(block.get("queue_depth", 1))
        except (TypeError, ValueError):
            depth = 1
        try:
            reader_workers = int(block.get("reader_workers", 1))
        except (TypeError, ValueError):
            reader_workers = 1
        reader_workers = max(1, min(_MAX_READER_WORKERS, reader_workers))
        prefetch = bool(block.get("prefetch_enabled", True))
        if not prefetch:
            depth = 1
            reader_workers = 1
        else:
            depth = max(1, min(_MAX_QUEUE_DEPTH, depth))
            if reader_workers > 1:
                depth = max(depth, min(reader_workers, _MAX_QUEUE_DEPTH))
        return cls(
            queue_depth=depth,
            prefetch_enabled=prefetch,
            reader_workers=reader_workers,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "queue_depth": self.queue_depth,
            "prefetch_enabled": self.prefetch_enabled,
            "reader_workers": self.reader_workers,
        }


__all__ = ["CalendarSliceRuntimeSettings"]
