"""Worker 并行度探针（替代 module_name + worker.json 路径）。"""
from __future__ import annotations

import logging
import multiprocessing as mp
from typing import Optional, Union

logger = logging.getLogger(__name__)


class WorkerProbe:
    """解析 max_workers，供 create_job_executor / JobPipeline 使用。"""

    @classmethod
    def resolve(
        cls,
        max_workers: Union[str, int],
        *,
        reserve_cores: int = 1,
        cap: Optional[int] = None,
    ) -> int:
        """
        解析并行 worker 数。

        - ``"auto"``：``mp.cpu_count() - reserve_cores``（为 OS + 主进程留核）
        - 整数：校验 ∈ [1, cpu×2]
        """
        if isinstance(max_workers, str) and max_workers.lower() == "auto":
            resolved = cls._auto(reserve_cores=reserve_cores, cap=cap)
            logger.info(
                "Worker 数量（auto/probe）: %s (cpu=%s, reserve=%s, cap=%s)",
                resolved,
                mp.cpu_count(),
                reserve_cores,
                cap,
            )
            return resolved

        validated = cls._validate_int(int(max_workers))
        if validated != max_workers:
            logger.warning(
                "Worker 数量超过上限，已调整: %s → %s (max=%s)",
                max_workers,
                validated,
                (mp.cpu_count() or 1) * 2,
            )
        return validated

    @staticmethod
    def _auto(*, reserve_cores: int, cap: Optional[int]) -> int:
        cpu_count = mp.cpu_count() or 1
        reserve = max(0, min(int(reserve_cores), cpu_count - 1))
        workers = max(1, cpu_count - reserve)
        if cap is not None:
            workers = min(workers, max(1, int(cap)))
        return WorkerProbe._validate_int(workers)

    @staticmethod
    def _validate_int(max_workers: int) -> int:
        cpu_count = mp.cpu_count() or 1
        max_allowed = cpu_count * 2
        return min(max(1, max_workers), max_allowed)
