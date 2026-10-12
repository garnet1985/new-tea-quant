"""主线程按字节把映射后的表攒进缓冲区，到顶后分块写入。"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from core.modules.data_source.core.service.executor.bundle_progress import BundleExecutionProgress
from core.modules.data_source.core.service.pipeline.frame_mapping import frame_nbytes
from core.modules.data_source.core.service.pipeline.save_memory_budget import SaveMemoryBudget
from core.modules.data_source.core.service.pipeline.save_utils import checkpoint_after_batch_save

logger = logging.getLogger(__name__)

ToFrames = Callable[[Dict[str, Any], Any, Dict[str, Any]], List[pd.DataFrame]]
SaveFrames = Callable[[Dict[str, Any], List[pd.DataFrame]], None]


class DataSourceSaveBuffer:
    """缓冲区里只放映射后的 DataFrame。超过字节上限先写入再放入下一笔。"""

    def __init__(
        self,
        *,
        context: Dict[str, Any],
        budget: SaveMemoryBudget,
        to_frames: ToFrames,
        save_frames: SaveFrames,
        bundle_progress: Optional[BundleExecutionProgress] = None,
    ) -> None:
        self._context = context
        self._budget = budget
        self._to_frames = to_frames
        self._save_frames = save_frames
        self._bundle_progress = bundle_progress
        self._frames: List[pd.DataFrame] = []
        self._bytes = 0
        self._bundles = 0

    def add(self, job_bundle: Any, result: Dict[str, Any]) -> None:
        produced = [
            frame
            for frame in (self._to_frames(self._context, job_bundle, result) or [])
            if isinstance(frame, pd.DataFrame) and not frame.empty
        ]
        if not produced:
            return
        self._bundles += 1
        for frame in produced:
            nbytes = frame_nbytes(frame)
            self._budget.observe(nbytes)
            self._budget.warn_if_frame_exceeds(nbytes)
            cap = self._budget.buffer_cap
            if self._frames and self._bytes + nbytes > cap:
                self._flush()
            if nbytes > cap or cap <= 0:
                self._write([frame], bundles=1 if not self._frames else 0)
                continue
            self._frames.append(frame)
            self._bytes += nbytes
            if self._bytes >= cap:
                self._flush()

    def flush_remaining(self) -> None:
        if self._frames:
            self._flush()

    def _flush(self) -> None:
        if not self._frames:
            return
        frames = self._frames
        count = self._bundles
        self._frames = []
        self._bytes = 0
        self._bundles = 0
        self._write(frames, bundles=count)

    def _write(self, frames: List[pd.DataFrame], *, bundles: int) -> None:
        try:
            self._save_frames(self._context, frames)
        finally:
            self._budget.note_rss()
            if self._bundle_progress is not None and bundles:
                self._bundle_progress.add_saved(bundles)
            checkpoint_after_batch_save(self._context)
