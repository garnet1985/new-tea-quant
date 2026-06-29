"""
Backtest Scheduler - Shared基础工具函数

提供真正共用的基础工具函数（不包含完整的调度逻辑）。

完整调度逻辑应该在各自的调度器中：
- timeline_based/dispatch_planner.py：时间线模式的智能调度算法
- slice_based/scheduler.py：切片模式的调度逻辑
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

DEFAULT_WORKER_MEMORY_FRACTION: float = 0.85
# psutil 不可用时的最后兜底（应在 settings 中显式配置 memory_floor_mb）
_FALLBACK_MEMORY_FLOOR_MB: float = 2048.0
_FALLBACK_BUDGET_MB: float = 4096.0


def _get_virtual_memory_mb() -> Tuple[Optional[float], Optional[float]]:
    """获取系统虚拟内存信息（MB）。"""
    try:
        import psutil

        vm = psutil.virtual_memory()
        total = float(vm.total) / (1024.0 * 1024.0)
        available = float(vm.available) / (1024.0 * 1024.0)
        return total, available
    except Exception:
        return None, None


def resolve_memory_floor_mb(performance: Dict[str, Any]) -> float:
    """
    机器上必须保留的空闲内存（保底），不参与 worker 预算。

    ``memory_floor_mb``：显式 MB；``"auto"``：约 15% 总内存，且不少于 1GB。
    已废弃的 ``main_process_reserve_mb`` 若存在则并入 floor（取较大值）。
    """
    raw = performance.get("memory_floor_mb")
    if raw not in (None, "", "auto"):
        floor = max(0.0, float(raw))
    else:
        total_mb, available_mb = _get_virtual_memory_mb()
        if total_mb is None or available_mb is None:
            floor = _FALLBACK_MEMORY_FLOOR_MB
        else:
            pct = max(1024.0, total_mb * 0.15)
            floor = min(pct, max(1024.0, available_mb * 0.5))

    legacy = performance.get("main_process_reserve_mb")
    if legacy not in (None, ""):
        floor = max(floor, max(0.0, float(legacy)))
    return floor


def resolve_memory_budget_mb(performance: Dict[str, Any]) -> Tuple[float, float]:
    """返回 (worker 可用预算 MB, memory_floor_mb)。"""
    floor_mb = resolve_memory_floor_mb(performance)
    raw = performance.get("dispatch_memory_budget_mb") or performance.get(
        "memory_budget_mb"
    )
    if raw not in ("auto", None, ""):
        return max(256.0, float(raw)), floor_mb

    _total_mb, available_mb = _get_virtual_memory_mb()
    if available_mb is None:
        return _FALLBACK_BUDGET_MB, floor_mb

    usable = max(0.0, available_mb - floor_mb)
    fraction = float(
        performance.get("worker_memory_fraction", DEFAULT_WORKER_MEMORY_FRACTION)
    )
    fraction = max(0.1, min(1.0, fraction))
    budget = usable * fraction
    return max(256.0, min(budget, 16384.0)), floor_mb


__all__ = [
    "resolve_memory_budget_mb",
    "resolve_memory_floor_mb",
]