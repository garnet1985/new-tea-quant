"""开发用缓存清理（供 ``devcli.py`` 调用）。"""
from __future__ import annotations

from typing import Iterable

from core.infra.system_actions import SystemActions


def clear_simulation_disk_cache(*, strategy_names: Iterable[str] | None = None) -> int:
    """删除各策略 ``results/`` 目录（物理模拟 + 扫描产物，devcli）。"""
    return SystemActions.cache.clear_strategy_results(strategy_names=strategy_names)


def clear_simulation_cache_all(*, strategy_names: Iterable[str] | None = None) -> None:
    """删除物理 ``results/`` 并清空 ``sys_strategy_workbench_snapshot`` 表。"""
    SystemActions.cache.clear_strategy_results(strategy_names=strategy_names)
    SystemActions.cache.clear_workbench_db()


def clear_userspace_simulation_cache(*, strategy_names: Iterable[str] | None = None) -> None:
    """兼容 ``-cu``：等同 ``clear_simulation_cache_all``。"""
    clear_simulation_cache_all(strategy_names=strategy_names)


def clear_userspace_ntq_dir() -> None:
    SystemActions.cache.clear_userspace_ntq()


def clear_workbench_db_cache() -> int:
    return SystemActions.cache.clear_workbench_db()


__all__ = [
    "clear_simulation_cache_all",
    "clear_simulation_disk_cache",
    "clear_userspace_ntq_dir",
    "clear_userspace_simulation_cache",
    "clear_workbench_db_cache",
]
