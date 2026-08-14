"""
save_batch_size=auto 时的内存感知写入批次（data_source 内置，不依赖 infra.worker）。

逻辑与原先 save_batch_size=auto 的内存感知路径一致，实现在本模块内，renew 长跑不依赖其它调度包。
"""
from __future__ import annotations
from core.infra.cmd_layout import i

import logging
import os
from typing import Any, List, Optional

import psutil

from core.modules.data_source.core.service.executor.bundle_progress import (
    AUTO_MAX_SAVE_BATCH_SIZE,
)

logger = logging.getLogger(__name__)


def _rss_mb() -> float:
    return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)


def _available_memory_mb() -> float:
    try:
        mem = psutil.virtual_memory()
        return mem.available / (1024 * 1024)
    except Exception:
        return 4096.0


def _memory_budget_mb() -> float:
    available = _available_memory_mb()
    budget = available * 0.7
    return max(1024.0, min(budget, 16384.0))


def _initial_batch_sizes(total_jobs: int) -> tuple[int, int, int]:
    if total_jobs <= 0:
        return (20, 10, 500)
    if total_jobs < 100:
        warmup = min(10, max(1, total_jobs // 2))
        return (warmup, max(5, warmup // 2), min(100, total_jobs))
    if total_jobs < 1000:
        return (20, 10, 200)
    return (30, 10, 500)


class SaveBatchAutoSizer:
    """
    动态 save 批次：根据主进程 RSS 增量调整下一批 bundle 写入数量。

    供 SaveBatchSizer / DataSourceSaveBuffer 在 auto 模式下使用。
    """

    def __init__(
        self,
        *,
        total_bundles: int,
        max_batch_size: int = AUTO_MAX_SAVE_BATCH_SIZE,
        log: Optional[logging.Logger] = None,
    ) -> None:
        self.total_jobs = max(int(total_bundles), 0)
        self._log = log or logger

        budget = _memory_budget_mb()
        warmup, min_size, max_size = _initial_batch_sizes(self.total_jobs)
        self._max_batch_size = max(1, int(max_batch_size))
        self.min_batch_size = min_size
        self.max_batch_size = min(max_size, self._max_batch_size)
        self._memory_budget_mb = budget

        if self.total_jobs == 0:
            self.current_batch_size = 0
        else:
            initial = min(warmup, self.total_jobs)
            self.current_batch_size = max(initial, self.min_batch_size)

        self._baseline_rss_mb = _rss_mb()
        self._last_batch_rss: Optional[float] = None
        self.mem_working_per_job = 0.0
        self.mem_summary_per_job = 0.0
        self.finished_jobs = 0
        self._smooth_factor = 0.3
        self._summary_weight = 0.2

        self._log.info(f"{i('bar_chart')} 自动计算内存预算: %.1f MB", budget)
        self._log.info(
            i('bar_chart') + " 自动计算 batch sizes: warmup=%s, min=%s, max=%s",
            warmup,
            min_size,
            self.max_batch_size,
        )

    def get_next_batch_size(self) -> int:
        return max(1, self.current_batch_size)

    def record_batch_start(self) -> None:
        self._last_batch_rss = _rss_mb()

    def update_after_batch(
        self,
        batch_size: int,
        batch_results: List[Any],
        finished_jobs: int,
    ) -> None:
        del batch_results
        self.finished_jobs = finished_jobs
        delta_batch = 0.0
        if self._last_batch_rss is not None:
            delta_batch = max(_rss_mb() - self._last_batch_rss, 0.0)

        if batch_size > 0 and delta_batch > 0.0:
            mem_per_job = delta_batch / float(batch_size)
            mem_summary = mem_per_job * self._summary_weight
            mem_working = max(mem_per_job - mem_summary, 0.0)
            s = self._smooth_factor
            if self.mem_working_per_job <= 0.0:
                self.mem_working_per_job = mem_working
                self.mem_summary_per_job = mem_summary
            else:
                self.mem_working_per_job = (
                    self.mem_working_per_job * (1.0 - s) + mem_working * s
                )
                self.mem_summary_per_job = (
                    self.mem_summary_per_job * (1.0 - s) + mem_summary * s
                )

        self._adjust_batch_size()

    def _adjust_batch_size(self) -> None:
        if self.total_jobs <= 0:
            self.current_batch_size = 0
            return

        summary_used = max(self.finished_jobs * self.mem_summary_per_job, 0.0)
        available_for_working = max(self._memory_budget_mb - summary_used, 0.0)

        if self.mem_working_per_job > 0.0:
            target = int(available_for_working / self.mem_working_per_job)
        else:
            target = self.current_batch_size or self.min_batch_size

        target = max(self.min_batch_size, min(target, self.max_batch_size))
        current = self.current_batch_size or self.min_batch_size
        max_step = max(int(current * 0.5), 5)
        delta = max(-max_step, min(max_step, target - current))
        self.current_batch_size = max(
            self.min_batch_size,
            min(current + delta, self.max_batch_size),
        )
