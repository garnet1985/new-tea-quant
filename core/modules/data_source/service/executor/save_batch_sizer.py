"""
SaveBatchSizer - batch 模式下的写入批次大小（固定值或内存感知 auto）。
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional

from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_source.service.executor.bundle_progress import AUTO_MAX_SAVE_BATCH_SIZE

logger = logging.getLogger(__name__)


class SaveBatchSizer:
    """根据 save_mode / save_batch_size 决定何时触发合并写入。"""

    def __init__(
        self,
        config: DataSourceConfig,
        total_bundles: int,
        save_mode: str,
    ) -> None:
        self._save_mode = save_mode
        self._fixed_size: Optional[int] = None
        self._scheduler = None
        self._saved_bundles = 0

        if save_mode == "immediate":
            self._fixed_size = 1
        elif save_mode == "batch":
            if config.is_save_batch_size_auto():
                from core.modules.data_source.service.executor.save_batch_auto_sizer import (
                    SaveBatchAutoSizer,
                )

                self._scheduler = SaveBatchAutoSizer(
                    total_bundles=total_bundles,
                    max_batch_size=AUTO_MAX_SAVE_BATCH_SIZE,
                    log=logger,
                )
            else:
                self._fixed_size = config.get_save_batch_size()

    @property
    def save_mode(self) -> str:
        return self._save_mode

    def is_dynamic(self) -> bool:
        return self._scheduler is not None

    def current_size(self) -> int:
        if self._save_mode == "unified":
            return 0
        if self._scheduler is not None:
            return max(1, self._scheduler.get_next_batch_size())
        return max(1, self._fixed_size or 1)

    def record_batch_start(self) -> None:
        if self._scheduler is not None:
            self._scheduler.record_batch_start()

    def after_batch_saved(self, batch_size: int, batch_results: List[Any]) -> None:
        if self._scheduler is None:
            return
        self._saved_bundles += batch_size
        self._scheduler.update_after_batch(
            batch_size=batch_size,
            batch_results=batch_results,
            finished_jobs=self._saved_bundles,
        )
        logger.info(
            "📊 [save_batch_size=auto] 下一批写入阈值: %s（已写入 %s/%s bundles）",
            self.current_size(),
            self._saved_bundles,
            self._scheduler.total_jobs,
        )
