"""主进程 report 路径：攒批 tag_values 再 upsert。

消费者: TagValueFlushService
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List


class TagReportSaveBuffer:
    """按行数阈值缓冲 tag_values，达到 batch_size 或 flush 时一次 save_batch。"""

    def __init__(
        self,
        save_fn: Callable[[List[Dict[str, Any]]], int],
        *,
        batch_size: int = 5000,
    ) -> None:
        self._save_fn = save_fn
        self._batch_size = max(1, int(batch_size))
        self._buffer: List[Dict[str, Any]] = []
        self.saved_row_count = 0
        self.flush_count = 0

    @property
    def pending_row_count(self) -> int:
        return len(self._buffer)

    def extend(self, tag_values: List[Dict[str, Any]]) -> float:
        """追加 rows；若达到 batch_size 则 flush。返回本次触发的 save_batch 耗时（秒）。"""
        if not tag_values:
            return 0.0
        self._buffer.extend(tag_values)
        save_sec = 0.0
        while len(self._buffer) >= self._batch_size:
            save_sec += self._flush_chunk(self._batch_size)
        return save_sec

    def extend_in_chunks(self, tag_values: List[Dict[str, Any]]) -> float:
        """按 batch_size 切片追加，避免单次 extend 传入超大 list 常驻内存。"""
        if not tag_values:
            return 0.0
        save_sec = 0.0
        bs = self._batch_size
        for offset in range(0, len(tag_values), bs):
            save_sec += self.extend(tag_values[offset : offset + bs])
        return save_sec

    def flush(self) -> float:
        """写出剩余缓冲。返回 save_batch 耗时（秒）。"""
        if not self._buffer:
            return 0.0
        return self._flush_chunk(len(self._buffer))

    def _flush_chunk(self, count: int) -> float:
        chunk = self._buffer[:count]
        self._buffer = self._buffer[count:]
        t0 = time.perf_counter()
        affected = self._save_fn(chunk)
        self.saved_row_count += affected if affected else len(chunk)
        self.flush_count += 1
        return time.perf_counter() - t0


__all__ = ["TagReportSaveBuffer"]
