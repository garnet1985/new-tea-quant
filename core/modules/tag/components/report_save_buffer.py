"""主进程 report 路径：攒批 tag_values 再 upsert；stage_in_worker 支持 Parquet spill。"""
from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)


def _write_parquet_spill(rows: List[Dict[str, Any]], path: Path) -> None:
    import duckdb
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    path_sql = str(path.resolve()).replace("'", "''")
    con = duckdb.connect()
    try:
        df = pd.DataFrame(rows)
        con.register("_tag_spill_df", df)
        con.execute(f"COPY _tag_spill_df TO '{path_sql}' (FORMAT PARQUET)")
    finally:
        con.close()


def _iter_spill_batches(
    path: Path,
    batch_size: int,
) -> Iterator[List[Dict[str, Any]]]:
    """按批读出单个 Parquet spill（DuckDB LIMIT/OFFSET）。"""
    if path.suffix.lower() != ".parquet":
        raise ValueError(f"spill 须为 .parquet: {path}")

    bs = max(1, int(batch_size))
    import duckdb

    path_sql = str(path.resolve()).replace("'", "''")
    con = duckdb.connect()
    try:
        total = int(
            con.sql(f"SELECT count(*)::BIGINT FROM read_parquet('{path_sql}')").fetchone()[0]
        )
        for offset in range(0, total, bs):
            df = con.sql(
                f"SELECT * FROM read_parquet('{path_sql}') "
                f"LIMIT {bs} OFFSET {offset}"
            ).df()
            if df.empty:
                continue
            yield df.to_dict(orient="records")
    finally:
        con.close()


class TagReportSaveBuffer:
    """按行数阈值缓冲 tag_values，达到 batch_size 或 flush 时一次 save_batch。"""

    def __init__(
        self,
        save_fn: Callable[[List[Dict[str, Any]]], int],
        *,
        batch_size: int = 5000,
        accumulate_only: bool = False,
        spill_row_threshold: Optional[int] = None,
        spill_dir: Optional[Path] = None,
    ) -> None:
        self._save_fn = save_fn
        self._batch_size = max(1, int(batch_size))
        self._accumulate_only = bool(accumulate_only)
        self._spill_threshold = (
            max(1, int(spill_row_threshold)) if spill_row_threshold else None
        )
        self._spill_dir = Path(spill_dir) if spill_dir else None
        self._spill_files: List[Path] = []
        self._buffer: List[Dict[str, Any]] = []
        self.saved_row_count = 0
        self.flush_count = 0
        self.spill_count = 0

    @property
    def pending_row_count(self) -> int:
        """内存缓冲行数（不含已 spill 到磁盘的行）。"""
        return len(self._buffer)

    def extend(self, tag_values: List[Dict[str, Any]]) -> float:
        """追加 rows；若达到 batch_size 则 flush。返回本次触发的 save_batch 耗时（秒）。"""
        if not tag_values:
            return 0.0
        self._buffer.extend(tag_values)
        if self._accumulate_only:
            self._maybe_spill_to_disk()
            return 0.0
        save_sec = 0.0
        while len(self._buffer) >= self._batch_size:
            save_sec += self._flush_chunk(self._batch_size)
        return save_sec

    def extend_in_chunks(self, tag_values: List[Dict[str, Any]]) -> float:
        """
        按 batch_size 切片追加，避免单次 extend 传入超大 list 常驻内存。

        与 extend 等价，但峰值内存约为 O(batch_size + len(单切片))。
        """
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

    def persist_accumulated(
        self,
        save_fn: Callable[[List[Dict[str, Any]]], int],
        *,
        batch_size: Optional[int] = None,
    ) -> float:
        """
        stage_in_worker 收尾：按批读取 spill 文件 + 内存缓冲，写入 save_fn。
        """
        bs = max(1, int(batch_size or self._batch_size))
        t0 = time.perf_counter()
        total = 0
        for path in list(self._spill_files):
            for batch in _iter_spill_batches(path, bs):
                total += self._save_rows(save_fn, batch)
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("删除 spill 文件失败 %s: %s", path, exc)
        self._spill_files.clear()

        self._save_fn = save_fn
        while self._buffer:
            n = min(bs, len(self._buffer))
            chunk = self._buffer[:n]
            self._buffer = self._buffer[n:]
            total += self._save_rows(save_fn, chunk)

        self.saved_row_count += total
        return time.perf_counter() - t0

    def cleanup_spill_dir(self) -> None:
        if self._spill_dir is None or not self._spill_dir.exists():
            return
        try:
            shutil.rmtree(self._spill_dir, ignore_errors=True)
        except OSError as exc:
            logger.warning("清理 spill 目录失败 %s: %s", self._spill_dir, exc)

    def _save_rows(
        self,
        save_fn: Callable[[List[Dict[str, Any]]], int],
        rows: List[Dict[str, Any]],
    ) -> int:
        if not rows:
            return 0
        affected = int(save_fn(rows) or len(rows))
        self.flush_count += 1
        return affected if affected else len(rows)

    def _maybe_spill_to_disk(self) -> None:
        if (
            not self._accumulate_only
            or self._spill_threshold is None
            or self._spill_dir is None
            or len(self._buffer) < self._spill_threshold
        ):
            return
        self._spill_dir.mkdir(parents=True, exist_ok=True)
        path = self._spill_dir / f"chunk_{self.spill_count:05d}.parquet"
        n = len(self._buffer)
        _write_parquet_spill(list(self._buffer), path)
        self._spill_files.append(path)
        self.spill_count += 1
        self._buffer.clear()
        logger.debug("tag_values spill → %s (%d rows)", path.name, n)

    def _flush_chunk(self, count: int) -> float:
        chunk = self._buffer[:count]
        self._buffer = self._buffer[count:]
        t0 = time.perf_counter()
        affected = self._save_fn(chunk)
        self.saved_row_count += affected if affected else len(chunk)
        self.flush_count += 1
        return time.perf_counter() - t0
