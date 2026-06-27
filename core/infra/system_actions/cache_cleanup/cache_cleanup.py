"""Userspace cache cleanup (settings UI + devcli)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from core.infra.project_context import ProjectContext
from core.infra.system_actions.cache_cleanup.pipeline_lease import read_pipeline_status


def _rm_tree(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _discovered_strategy_keys(*, strategy_names: Optional[Iterable[str]] = None) -> List[str]:
    """策略 path key 列表；默认走 ``StrategyDiscoveryHelper`` 递归发现（与扫描/列表页一致）。"""
    if strategy_names is not None:
        return sorted({str(name).strip() for name in strategy_names if str(name).strip()})

    from core.modules.strategy.services.discovery import StrategyDiscoveryHelper
    from core.modules.strategy.services.discovery.path_rules import relative_strategy_key

    root = ProjectContext.path.get_strategies_root()
    if not root.is_dir():
        return []
    keys: List[str] = []
    for folder in StrategyDiscoveryHelper._iter_strategy_directories(root):
        try:
            keys.append(relative_strategy_key(folder, root))
        except ValueError:
            continue
    return sorted(keys)


def clear_workbench_db_cache() -> int:
    """清空 ``sys_strategy_workbench_snapshot`` 表。返回删除行数。"""
    from core.modules.strategy.launcher.workbench import clear_workbench_simulation_cache_all

    out = clear_workbench_simulation_cache_all()
    if not out.get("ok"):
        raise RuntimeError(str(out.get("error") or "存储不可用"))
    return int(out.get("deleted_count") or 0)


def clear_backtest_results_disk(*, strategy_names: Optional[Iterable[str]] = None) -> int:
    """删除各策略 ``results/simulations/``。返回删除的目录数。"""
    removed = 0
    for name in _discovered_strategy_keys(strategy_names=strategy_names):
        sim_root = ProjectContext.path.get_strategy_directory_results(name) / "simulations"
        if sim_root.exists():
            _rm_tree(sim_root)
            removed += 1
    return removed


def clear_scan_results_disk(*, strategy_names: Optional[Iterable[str]] = None) -> int:
    """删除各策略 ``results/scan/``。返回删除的目录数。"""
    removed = 0
    for name in _discovered_strategy_keys(strategy_names=strategy_names):
        scan_root = ProjectContext.path.get_strategy_directory_scan_results(name)
        if scan_root.exists():
            _rm_tree(scan_root)
            removed += 1
    return removed


def clear_strategy_results_disk(*, strategy_names: Optional[Iterable[str]] = None) -> int:
    """删除各策略整个 ``results/``（devcli 用，含 simulations 与 scan）。"""
    removed = 0
    for name in _discovered_strategy_keys(strategy_names=strategy_names):
        results = ProjectContext.path.get_strategy_directory_results(name)
        if results.exists():
            _rm_tree(results)
            removed += 1
    return removed


def clear_userspace_ntq_dir() -> None:
    """
    删除 ``userspace/.ntq/``（进度、pipeline 租约、tmp 等）。

    不触碰仓库根 ``.ntq/``（含 install-state 等开发缓存）。
    """
    ProjectContext.cache.clear_userspace_cache()
    us_ntq = ProjectContext.path.get_userspace_ntq_directory()
    if us_ntq.is_dir():
        _rm_tree(us_ntq)


def run_cache_cleanup(
    *,
    clear_db_cache: bool = False,
    clear_backtest_results: bool = False,
    clear_scan_results: bool = False,
    clear_userspace_ntq: bool = False,
) -> Dict[str, Any]:
    """
    按勾选项清理缓存。有全局 pipeline 任务进行中时拒绝（``error=pipeline_busy``）。
    """
    selected = [
        clear_db_cache,
        clear_backtest_results,
        clear_scan_results,
        clear_userspace_ntq,
    ]
    if not any(selected):
        return {"ok": False, "error": "nothing_selected"}

    pipeline = read_pipeline_status()
    if pipeline.get("busy"):
        return {
            "ok": False,
            "error": "pipeline_busy",
            "label": str(pipeline.get("label") or pipeline.get("kind") or "").strip(),
        }

    if clear_db_cache:
        clear_workbench_db_cache()
    if clear_backtest_results:
        clear_backtest_results_disk()
    if clear_scan_results:
        clear_scan_results_disk()
    if clear_userspace_ntq:
        clear_userspace_ntq_dir()

    return {"ok": True, "message": "缓存已经全部清理"}


__all__ = [
    "clear_backtest_results_disk",
    "clear_scan_results_disk",
    "clear_strategy_results_disk",
    "clear_userspace_ntq_dir",
    "clear_workbench_db_cache",
    "run_cache_cleanup",
]
