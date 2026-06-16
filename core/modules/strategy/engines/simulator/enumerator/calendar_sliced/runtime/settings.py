#!/usr/bin/env python3
"""calendar_slice 运行时调度参数（``worker.json`` → ``job_pipeline.enumerator.calendar_slice``）。

- ``reader_workers``：并行 Reader 进程数（``"auto"`` 或 1–8）
- ``queue_depth``：payload 队列容量 / preload 上限参考（``"auto"`` 或 1–8）
- ``prefetch_enabled``：关闭时强制单 reader、preload=1

片宽/步长由运行时 planner auto 决定，不在策略 settings 配置。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Union

from core.infra.job_pipeline.profile import WorkerProfiles, profile_calendar_slice_config
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.slice_plan import (
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
    def from_worker_profile(
        cls,
        worker_id: str = WorkerProfiles.ENUMERATOR,
    ) -> "CalendarSliceRuntimeSettings":
        block = profile_calendar_slice_config(worker_id)
        return cls._from_block(block)

    @classmethod
    def _from_block(cls, block: Dict[str, Any]) -> "CalendarSliceRuntimeSettings":
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


__all__ = ["CalendarSliceRuntimeSettings"]
