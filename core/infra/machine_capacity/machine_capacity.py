"""MachineInfo 门面（Facade）— infra.machine_capacity 对外统一入口类。

容量快照类型见 ``contracts.MachineCapacity``，亦可经 ``MachineInfo.types``。
"""
from __future__ import annotations

import logging
import multiprocessing as mp
from typing import Any, Dict, Optional, Tuple

from core.infra.machine_capacity.contracts import MachineCapacity

logger = logging.getLogger(__name__)


class TypesNamespace:
    """与 ``contracts`` 同源的类型挂载点。"""

    MachineCapacity = MachineCapacity


class MachineInfo:
    """New Tea Quant（NTQ）机器容量门面类（Facade）。"""

    types = TypesNamespace

    DEFAULT_WORKER_MEMORY_FRACTION: float = 0.85
    FALLBACK_MEMORY_FLOOR_MB: float = 2048.0
    FALLBACK_BUDGET_MB: float = 4096.0
    MIN_BUDGET_MB: float = 256.0
    MAX_BUDGET_MB: float = 16384.0
    AUTO_FLOOR_TOTAL_FRACTION: float = 0.15
    AUTO_FLOOR_AVAILABLE_FRACTION: float = 0.5
    AUTO_FLOOR_MIN_MB: float = 1024.0
    DEFAULT_RESERVE_CORES: int = 1

    @staticmethod
    def get_capacity(performance: Dict[str, Any]) -> MachineCapacity:
        """获取机器容量信息（CPU 和内存预算）。"""
        cpu_count = MachineInfo.get_cpu_count()
        reserve_cores = MachineInfo.get_reserve_cores(performance)
        memory_budget_mb, memory_floor_mb = MachineInfo.resolve_memory_budget(
            performance
        )
        return MachineCapacity(
            cpu_count=cpu_count,
            memory_budget_mb=memory_budget_mb,
            memory_floor_mb=memory_floor_mb,
            reserve_cores=reserve_cores,
        )

    @staticmethod
    def get_cpu_count() -> int:
        """获取 CPU 核心数（至少 1）。"""
        return mp.cpu_count() or 1

    @staticmethod
    def get_reserve_cores(performance: Dict[str, Any]) -> int:
        """从 ``performance.reserve_cores`` 解析预留核（默认 1）。"""
        try:
            reserve_cores = int(
                performance.get("reserve_cores", MachineInfo.DEFAULT_RESERVE_CORES)
            )
        except (TypeError, ValueError):
            reserve_cores = MachineInfo.DEFAULT_RESERVE_CORES
        return max(0, reserve_cores)

    @staticmethod
    def resolve_memory_floor(performance: Dict[str, Any]) -> float:
        """机器上必须保留的空闲内存（保底），不参与 worker 预算。"""
        raw = performance.get("memory_floor_mb")
        if raw not in (None, "", "auto"):
            return max(0.0, float(raw))

        total_mb, available_mb = MachineInfo.virtual_memory_mb()
        if total_mb is None or available_mb is None:
            return MachineInfo.FALLBACK_MEMORY_FLOOR_MB

        pct = max(
            MachineInfo.AUTO_FLOOR_MIN_MB,
            total_mb * MachineInfo.AUTO_FLOOR_TOTAL_FRACTION,
        )
        return min(
            pct,
            max(
                MachineInfo.AUTO_FLOOR_MIN_MB,
                available_mb * MachineInfo.AUTO_FLOOR_AVAILABLE_FRACTION,
            ),
        )

    @staticmethod
    def resolve_memory_budget(performance: Dict[str, Any]) -> Tuple[float, float]:
        """返回 ``(worker 可用预算 MB, memory_floor_mb)``。"""
        floor_mb = MachineInfo.resolve_memory_floor(performance)
        raw = performance.get("memory_budget_mb")
        if raw not in ("auto", None, ""):
            return max(MachineInfo.MIN_BUDGET_MB, float(raw)), floor_mb

        _total_mb, available_mb = MachineInfo.virtual_memory_mb()
        if available_mb is None:
            return MachineInfo.FALLBACK_BUDGET_MB, floor_mb

        usable = max(0.0, available_mb - floor_mb)
        try:
            fraction = float(
                performance.get(
                    "worker_memory_fraction",
                    MachineInfo.DEFAULT_WORKER_MEMORY_FRACTION,
                )
            )
        except (TypeError, ValueError):
            fraction = MachineInfo.DEFAULT_WORKER_MEMORY_FRACTION
        fraction = max(0.1, min(1.0, fraction))
        budget = usable * fraction
        return (
            max(MachineInfo.MIN_BUDGET_MB, min(budget, MachineInfo.MAX_BUDGET_MB)),
            floor_mb,
        )

    @staticmethod
    def get_available_workers(capacity: MachineCapacity) -> int:
        """可用 worker 数：``cpu_count − reserve_cores``（至少 1）。"""
        return max(1, capacity.cpu_count - capacity.reserve_cores)

    @staticmethod
    def worker_pool_budget_mb(capacity: MachineCapacity) -> float:
        """进程池并发可用的内存预算（MB）；至少 1。"""
        return max(1.0, float(capacity.memory_budget_mb))

    @staticmethod
    def parse_max_parallel_jobs_cap(raw: Any) -> Optional[int]:
        """解析并行 job 上限；``None`` / 空 / ``\"null\"`` / 非法 → ``None``。"""
        if raw in (None, "", "null", "auto"):
            return None
        try:
            return max(1, int(raw))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def virtual_memory_mb() -> Tuple[Optional[float], Optional[float]]:
        """本机 ``(total_mb, available_mb)``；无 psutil 或读取失败时返回 ``(None, None)``。"""
        try:
            import psutil
        except ImportError:
            return None, None
        try:
            vm = psutil.virtual_memory()
            total = float(vm.total) / (1024.0 * 1024.0)
            available = float(vm.available) / (1024.0 * 1024.0)
            return total, available
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            logger.debug("virtual_memory_mb unavailable: %s", exc)
            return None, None


__all__ = ["MachineInfo"]
