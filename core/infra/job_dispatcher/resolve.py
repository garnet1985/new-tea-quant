"""解析 max_workers（含 auto），供 create_job_executor 使用。"""
from __future__ import annotations

import logging
import multiprocessing as mp
from typing import Union

from core.infra.project_context import ConfigManager
from core.infra.worker.multi_process.task_type import TaskType

logger = logging.getLogger(__name__)


def calculate_workers(task_type: TaskType, reserve_cores: int = 2) -> int:
    """按 TaskType 计算建议 worker 数。"""
    return _calculate_workers(task_type, reserve_cores)


def resolve_max_workers(max_workers: Union[str, int], module_name: str) -> int:
    """
    解析并行 worker 数。

    - ``"auto"``：按 module 配置与 TaskType 计算
    - 数字：校验上限（不超过 CPU×2）
    """
    if isinstance(max_workers, str) and max_workers.lower() == "auto":
        config = ConfigManager.get_module_config(module_name)
        task_type = config["task_type"]
        reserve_cores = config["reserve_cores"]
        calculated = calculate_workers(task_type, reserve_cores)
        logger.info(
            "Worker 数量（auto）: %s (module=%s, type=%s, cpu=%s, reserve=%s)",
            calculated,
            module_name,
            task_type.value,
            mp.cpu_count(),
            reserve_cores,
        )
        return calculated

    validated = _validate_workers(int(max_workers))
    if validated != max_workers:
        logger.warning(
            "Worker 数量超过上限，已调整: %s → %s (max=%s)",
            max_workers,
            validated,
            (mp.cpu_count() or 1) * 2,
        )
    return validated


def _calculate_workers(task_type: TaskType, reserve_cores: int) -> int:
    cpu_count = mp.cpu_count() or 1
    if task_type == TaskType.CPU_INTENSIVE:
        physical_cores = max(1, cpu_count // 2)
        return max(1, physical_cores - reserve_cores)
    if task_type == TaskType.IO_INTENSIVE:
        return max(2, cpu_count - reserve_cores + 1)
    return max(1, cpu_count - reserve_cores)


def _validate_workers(max_workers: int) -> int:
    cpu_count = mp.cpu_count() or 1
    max_allowed = cpu_count * 2
    return min(max(1, max_workers), max_allowed)
