"""主进程 on_result 攒批写库（DuckDB 友好）。"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.service.executor.bundle_progress import BundleExecutionProgress
from core.modules.data_source.service.executor.save_batch_sizer import SaveBatchSizer
from core.modules.data_source.service.pipeline.save_utils import (
    BundleSaveItem,
    checkpoint_after_batch_save,
    invoke_bundle_save,
    is_duckdb_context,
)

logger = logging.getLogger(__name__)

DEFAULT_DUCKDB_IMMEDIATE_FLUSH_SIZE = 32


class DataSourceSaveBuffer:
    """
    在 on_result 中累积 bundle 结果，达到阈值后调用 handler 保存钩子。

    - unified：不写入
    - batch：沿用 SaveBatchSizer
    - immediate + DuckDB：按 batch 阈值 flush（避免频繁小写）
    - immediate + 非 DuckDB：阈值为 1，行为接近原 immediate
    """

    def __init__(
        self,
        *,
        context: Dict[str, Any],
        config: DataSourceConfig,
        save_mode: str,
        total_bundles: int,
        on_single_bundle_complete: Callable[[Dict[str, Any], Any, Dict[str, Any]], Any],
        on_batch_bundles_complete: Callable[[Dict[str, Any], List[BundleSaveItem]], Any],
        bundle_progress: Optional[BundleExecutionProgress] = None,
    ) -> None:
        self._context = context
        self._save_mode = save_mode
        self._on_single = on_single_bundle_complete
        self._on_batch = on_batch_bundles_complete
        self._bundle_progress = bundle_progress
        self._pending: List[BundleSaveItem] = []
        self._flush_count = 0

        if save_mode == "unified":
            self._sizer = None
            self._flush_save_mode = "unified"
            return

        if save_mode == "immediate" and is_duckdb_context(context):
            self._sizer = _DuckdbImmediateBatchSizer(config, total_bundles)
            self._flush_save_mode = "batch"
        else:
            self._sizer = SaveBatchSizer(config, total_bundles, save_mode)
            self._flush_save_mode = (
                "immediate" if save_mode == "immediate" else "batch"
            )

    @property
    def saves_enabled(self) -> bool:
        return self._save_mode != "unified"

    def add(self, job_bundle: Any, result: Dict[str, Any]) -> None:
        if not self.saves_enabled or self._sizer is None:
            return
        self._pending.append((job_bundle, result))
        threshold = self._sizer.current_size()
        if len(self._pending) >= threshold:
            self._flush_pending()

    def flush_remaining(self) -> None:
        if self._pending:
            self._flush_pending()

    def _flush_pending(self) -> None:
        if not self._pending:
            return
        batch = list(self._pending)
        self._pending.clear()
        self._sizer.record_batch_start()
        try:
            n = invoke_bundle_save(
                self._context,
                batch,
                self._flush_save_mode,
                self._on_single,
                self._on_batch,
            )
            self._flush_count += 1
            logger.debug(
                "pipeline 写库 flush: %s bundles（mode=%s, 调度次数≈%s）",
                len(batch),
                self._flush_save_mode,
                1 if self._flush_save_mode == "batch" and n else n,
            )
        except Exception as e:
            logger.error("pipeline 写库 flush 失败: %s", e, exc_info=True)
            raise
        finally:
            self._sizer.after_batch_saved(len(batch), batch)
            if self._bundle_progress is not None:
                self._bundle_progress.add_saved(len(batch))
            checkpoint_after_batch_save(self._context)


class _DuckdbImmediateBatchSizer:
    """immediate + DuckDB：用 batch 合并写，阈值来自 config 或默认。"""

    def __init__(self, config: DataSourceConfig, total_bundles: int) -> None:
        if config.is_save_batch_size_auto():
            from core.infra.worker import MemoryAwareScheduler
            from core.modules.data_source.service.executor.bundle_progress import (
                AUTO_MAX_SAVE_BATCH_SIZE,
            )

            placeholders = [None] * max(total_bundles, 1)
            self._scheduler = MemoryAwareScheduler(
                jobs=placeholders,
                max_batch_size=AUTO_MAX_SAVE_BATCH_SIZE,
                log=logger,
            )
            self._fixed_size: Optional[int] = None
        else:
            self._scheduler = None
            raw = config.get_save_batch_size()
            self._fixed_size = max(
                1,
                int(raw) if raw else DEFAULT_DUCKDB_IMMEDIATE_FLUSH_SIZE,
            )
        self._saved_bundles = 0

    def current_size(self) -> int:
        if self._scheduler is not None:
            return max(1, self._scheduler.get_next_batch_size())
        return max(1, self._fixed_size or DEFAULT_DUCKDB_IMMEDIATE_FLUSH_SIZE)

    def record_batch_start(self) -> None:
        if self._scheduler is not None:
            self._scheduler.monitor.record_batch_start()

    def after_batch_saved(self, batch_size: int, batch_results: List[Any]) -> None:
        if self._scheduler is None:
            return
        self._saved_bundles += batch_size
        self._scheduler.update_after_batch(
            batch_size=batch_size,
            batch_results=batch_results,
            finished_jobs=self._saved_bundles,
        )
