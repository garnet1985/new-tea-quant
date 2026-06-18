"""开发用缓存清理（供 ``devcli.py`` 调用）。"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable


def _rm_tree(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def clear_userspace_ntq_dir() -> None:
    """
    删除 ``userspace/.ntq/``（升级 inbox、update 缓存、tmp 等；含 legacy ``system/.ntq`` 合并）。

    不触碰仓库根 ``.ntq/``（含 ``install-state.json`` 与其它开发缓存）。
    """
    try:
        from core.infra.project_context.path_manager import PathManager

        PathManager.invalidate_userspace_cache()
        us_ntq = PathManager.userspace_ntq()
        if us_ntq.is_dir():
            print(f"删除 {us_ntq}", flush=True)
            _rm_tree(us_ntq)
        else:
            print(f"无 {us_ntq}，跳过。", flush=True)
    except Exception as exc:
        print(f"userspace/.ntq 清理失败: {exc}", flush=True)


def _strategy_names_on_disk() -> list[str]:
    from core.infra.project_context.path_manager import PathManager

    root = PathManager.strategies_root()
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))


def clear_simulation_disk_cache(*, strategy_names: Iterable[str] | None = None) -> int:
    """删除各策略 ``results/`` 目录（物理模拟产物）。返回删除的目录数。"""
    from core.infra.project_context.path_manager import PathManager

    names = list(strategy_names) if strategy_names is not None else _strategy_names_on_disk()
    removed = 0
    for name in names:
        results = PathManager.strategy_results(name)
        if results.exists():
            print(f"删除 {results}", flush=True)
            _rm_tree(results)
            removed += 1
    if removed == 0:
        print("无策略 results/ 目录，跳过磁盘清理。", flush=True)
    return removed


def clear_workbench_db_cache() -> int:
    """清空 ``sys_strategy_workbench_snapshot`` 表（模拟结果 DbCache）。返回删除行数。"""
    try:
        from core.modules.strategy.services.cache.simulator_res_db_cache.cache_service import (
            SimulatorResDbCacheService,
        )

        svc = SimulatorResDbCacheService()
        if svc.table_operator is None:
            print("DB 表 sys_strategy_workbench_snapshot 未注册，跳过数据库清理。", flush=True)
            return 0
        n = int(svc.delete_all_cache() or 0)
        if n > 0:
            print(f"DB 已删除 {n} 条工作台快照", flush=True)
        else:
            print("DB 工作台快照表已为空。", flush=True)
        return n
    except Exception as exc:
        print(f"DB 工作台快照清理失败（请确认数据库可用）: {exc}", flush=True)
        return 0


def clear_simulation_cache_all(*, strategy_names: Iterable[str] | None = None) -> None:
    """删除物理 ``results/`` 并清空 ``sys_strategy_workbench_snapshot`` 表。"""
    clear_simulation_disk_cache(strategy_names=strategy_names)
    clear_workbench_db_cache()


def clear_userspace_simulation_cache(*, strategy_names: Iterable[str] | None = None) -> None:
    """兼容 ``-cu``：等同 ``clear_simulation_cache_all``。"""
    clear_simulation_cache_all(strategy_names=strategy_names)
