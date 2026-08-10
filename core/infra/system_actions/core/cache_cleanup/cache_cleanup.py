"""Userspace cache cleanup (settings UI + devcli)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from core.infra.project_context import ProjectContext
from core.infra.system_actions.core.cache_cleanup.pipeline_lease import PipelineLease


class CacheCleanup:
    """缓存清理操作（方法挂靠本类，不作为模块自由函数导出）。"""

    @staticmethod
    def _rm_tree(path: Path) -> None:
        if not path.exists():
            return
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    @staticmethod
    def _discovered_strategy_folders(
        *, strategy_names: Optional[Iterable[str]] = None
    ) -> List[Path]:
        """Discovered strategy roots (absolute). Optional filter by key or relative path."""
        from core.modules.strategy import Strategy

        if strategy_names is not None:
            allowed = sorted(
                {str(name).strip() for name in strategy_names if str(name).strip()}
            )
            folders: List[Path] = []
            seen: set[str] = set()
            infos = Strategy.list_strategy_infos()
            for name in allowed:
                matched = False
                for info in infos:
                    if name in (
                        str(info.get("unique_relative_path") or "").strip(),
                        str(info.get("key") or "").strip(),
                    ):
                        folder = Path(str(info["folder"]))
                        key = str(folder)
                        if key not in seen:
                            seen.add(key)
                            folders.append(folder)
                        matched = True
                        break
                if not matched:
                    folder = Strategy.resolve_folder(name)
                    key = str(folder)
                    if key not in seen:
                        seen.add(key)
                        folders.append(folder)
            return folders

        out: List[Path] = []
        seen_all: set[str] = set()
        for info in Strategy.list_strategy_infos():
            folder = Path(str(info["folder"]))
            key = str(folder)
            if key not in seen_all:
                seen_all.add(key)
                out.append(folder)
        return out

    @staticmethod
    def clear_workbench_db_cache() -> int:
        """清空 ``sys_strategy_workbench_snapshot`` 表。返回删除行数。"""
        from core.modules.strategy import Strategy

        return Strategy.clear_workbench_cache()

    @staticmethod
    def clear_backtest_results_disk(
        *, strategy_names: Optional[Iterable[str]] = None
    ) -> int:
        """删除各策略 ``results/simulations/``。返回删除的目录数。"""
        removed = 0
        for folder in CacheCleanup._discovered_strategy_folders(
            strategy_names=strategy_names
        ):
            sim_root = (
                ProjectContext.path.get_strategy_results_directory(folder)
                / "simulations"
            )
            if sim_root.exists():
                CacheCleanup._rm_tree(sim_root)
                removed += 1
        return removed

    @staticmethod
    def clear_scan_results_disk(
        *, strategy_names: Optional[Iterable[str]] = None
    ) -> int:
        """删除各策略 ``results/scan/``。返回删除的目录数。"""
        removed = 0
        for folder in CacheCleanup._discovered_strategy_folders(
            strategy_names=strategy_names
        ):
            scan_root = ProjectContext.path.get_strategy_scan_results_directory(folder)
            if scan_root.exists():
                CacheCleanup._rm_tree(scan_root)
                removed += 1
        return removed

    @staticmethod
    def clear_strategy_results_disk(
        *, strategy_names: Optional[Iterable[str]] = None
    ) -> int:
        """删除各策略整个 ``results/``（含 simulations 与 scan；devcli 一键用）。"""
        removed = 0
        for folder in CacheCleanup._discovered_strategy_folders(
            strategy_names=strategy_names
        ):
            results = ProjectContext.path.get_strategy_results_directory(folder)
            if results.exists():
                CacheCleanup._rm_tree(results)
                removed += 1
        return removed

    @staticmethod
    def clear_userspace_ntq_dir() -> None:
        """
        删除 ``userspace/.ntq/``（进度、pipeline 租约、tmp 等）。

        不触碰仓库根 ``.ntq/``（含 install-state 等开发缓存）。
        """
        ProjectContext.cache.clear_userspace_cache()
        us_ntq = ProjectContext.path.get_userspace_ntq_directory()
        if us_ntq.is_dir():
            CacheCleanup._rm_tree(us_ntq)

    @staticmethod
    def run(
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

        pipeline = PipelineLease.read_status()
        if pipeline.get("busy"):
            return {
                "ok": False,
                "error": "pipeline_busy",
                "label": str(
                    pipeline.get("label") or pipeline.get("kind") or ""
                ).strip(),
            }

        if clear_db_cache:
            CacheCleanup.clear_workbench_db_cache()
        if clear_backtest_results:
            CacheCleanup.clear_backtest_results_disk()
        if clear_scan_results:
            CacheCleanup.clear_scan_results_disk()
        if clear_userspace_ntq:
            CacheCleanup.clear_userspace_ntq_dir()

        return {"ok": True, "message": "缓存已经全部清理"}
