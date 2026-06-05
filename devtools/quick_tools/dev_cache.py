"""开发用缓存清理（供 ``dev-cli.py`` 调用）。"""
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


def clear_userspace_simulation_cache(*, strategy_names: Iterable[str] | None = None) -> None:
    """删除各策略 ``results/`` 目录，并清空 ``sys_strategy_workbench_snapshot`` 表。"""
    from core.infra.project_context.path_manager import PathManager

    names = list(strategy_names) if strategy_names is not None else _strategy_names_on_disk()
    for name in names:
        results = PathManager.strategy_results(name)
        if results.exists():
            print(f"删除 {results}", flush=True)
            _rm_tree(results)

    try:
        from core.modules.strategy.services.cache.simulator_res_db_cache.cache_service import (
            SimulatorResDbCacheService,
        )

        svc = SimulatorResDbCacheService()
        model = svc.table_operator
        if model is None:
            print("DB 表 sys_strategy_workbench_snapshot 未注册，跳过数据库清理。", flush=True)
            return

        model._ensure_table_ready()
        db_names: set[str] = set()
        rows = model.execute_raw_query(
            f"SELECT DISTINCT strategy_name FROM {model.table_name}",
            (),
        )
        for row in rows or []:
            n = row.get("strategy_name")
            if isinstance(n, str) and n.strip():
                db_names.add(n.strip())
        for name in sorted(db_names | set(names)):
            n = model.delete("strategy_name = %s", (name,))
            if int(n or 0) > 0:
                print(f"DB 已删除策略 {name!r} 的 {n} 条快照", flush=True)
    except Exception as exc:
        print(f"DB 工作台快照清理失败（请确认数据库可用）: {exc}", flush=True)
