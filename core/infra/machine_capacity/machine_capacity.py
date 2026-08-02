"""MachineInfo 门面（Facade）— infra.machine_capacity 对外统一入口类。

容量快照类型见 ``contracts.MachineCapacity``。
"""
from __future__ import annotations

import logging
import multiprocessing as mp
from typing import Any, Dict, Optional, Tuple

from core.infra.machine_capacity.contracts import MachineCapacity

logger = logging.getLogger(__name__)

DEFAULT_WORKER_MEMORY_FRACTION: float = 0.85
_FALLBACK_MEMORY_FLOOR_MB: float = 2048.0
_FALLBACK_BUDGET_MB: float = 4096.0


class MachineInfo:
    """New Tea Quant（NTQ）机器容量门面类（Facade）。"""

    @staticmethod
    def get_capacity(performance: Dict[str, Any]) -> MachineCapacity:
        """获取机器容量信息（CPU和内存预算）。"""
        cpu_count = MachineInfo.get_cpu_count()
        reserve_cores = MachineInfo.get_reserve_cores(performance)
        memory_budget_mb, memory_floor_mb = MachineInfo.resolve_memory_budget(performance)
        return MachineCapacity(
            cpu_count=cpu_count,
            memory_budget_mb=memory_budget_mb,
            memory_floor_mb=memory_floor_mb,
            reserve_cores=reserve_cores,
        )

    @staticmethod
    def get_cpu_count() -> int:
        """获取CPU核心数。"""
        return mp.cpu_count() or 1

    @staticmethod
    def get_reserve_cores(performance: Dict[str, Any]) -> int:
        """获取保留核心数。"""
        try:
            reserve_cores = int(performance.get("reserve_cores", 1))
        except (TypeError, ValueError):
            reserve_cores = 1
        return max(0, reserve_cores)

    @staticmethod
    def get_memory_budget(performance: Dict[str, Any]) -> float:
        """获取 worker 内存预算（MB）。"""
        budget_mb, _ = MachineInfo.resolve_memory_budget(performance)
        return budget_mb

    @staticmethod
    def get_memory_floor(performance: Dict[str, Any]) -> float:
        """获取内存底线（MB）。"""
        return MachineInfo.resolve_memory_floor(performance)

    @staticmethod
    def resolve_memory_floor(performance: Dict[str, Any]) -> float:
        """机器上必须保留的空闲内存（保底），不参与 worker 预算。"""
        raw = performance.get("memory_floor_mb")
        if raw not in (None, "", "auto"):
            floor = max(0.0, float(raw))
        else:
            total_mb, available_mb = MachineInfo._virtual_memory_mb()
            if total_mb is None or available_mb is None:
                floor = _FALLBACK_MEMORY_FLOOR_MB
            else:
                pct = max(1024.0, total_mb * 0.15)
                floor = min(pct, max(1024.0, available_mb * 0.5))

        legacy = performance.get("main_process_reserve_mb")
        if legacy not in (None, ""):
            floor = max(floor, max(0.0, float(legacy)))
        return floor

    @staticmethod
    def resolve_memory_budget(performance: Dict[str, Any]) -> Tuple[float, float]:
        """返回 (worker 可用预算 MB, memory_floor_mb)。"""
        floor_mb = MachineInfo.resolve_memory_floor(performance)
        raw = performance.get("dispatch_memory_budget_mb") or performance.get(
            "memory_budget_mb"
        )
        if raw not in ("auto", None, ""):
            return max(256.0, float(raw)), floor_mb

        _total_mb, available_mb = MachineInfo._virtual_memory_mb()
        if available_mb is None:
            return _FALLBACK_BUDGET_MB, floor_mb

        usable = max(0.0, available_mb - floor_mb)
        try:
            fraction = float(
                performance.get("worker_memory_fraction", DEFAULT_WORKER_MEMORY_FRACTION)
            )
        except (TypeError, ValueError):
            fraction = DEFAULT_WORKER_MEMORY_FRACTION
        fraction = max(0.1, min(1.0, fraction))
        budget = usable * fraction
        return max(256.0, min(budget, 16384.0)), floor_mb

    @staticmethod
    def get_available_workers(capacity: MachineCapacity) -> int:
        """获取可用的 worker 数量（CPU 数 − 预留核心）。"""
        return max(1, capacity.cpu_count - capacity.reserve_cores)

    @staticmethod
    def worker_pool_budget_mb(capacity: MachineCapacity) -> float:
        """进程池并发可用的内存预算（MB）。"""
        return max(1.0, float(capacity.memory_budget_mb))

    @staticmethod
    def parse_max_parallel_jobs_cap(raw: Any) -> Optional[int]:
        if raw in (None, "", "null"):
            return None
        try:
            return max(1, int(raw))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _virtual_memory_mb() -> Tuple[Optional[float], Optional[float]]:
        try:
            import psutil

            vm = psutil.virtual_memory()
            total = float(vm.total) / (1024.0 * 1024.0)
            available = float(vm.available) / (1024.0 * 1024.0)
            return total, available
        except Exception:
            return None, None


__all__ = ["MachineInfo"]
