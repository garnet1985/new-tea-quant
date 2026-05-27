#!/usr/bin/env python3
"""
工作台 DB 快照行（``sys_strategy_workbench_snapshot.version``）保留与删除审计。

不直接删除磁盘 ``output_version`` 目录；删行时记录 ``result_report`` 中的路径引用，
便于排查 orphan 磁盘目录（清理由 ``simulation_output_retention`` 负责）。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.modules.data_manager import DataManager

from .simulation_output_retention import _protected_dirs_from_result_report

logger = logging.getLogger(__name__)


def _max_workbench_rows() -> int:
    from ...cache.simulator_res_db_cache.config import MAX_SNAPSHOT_ROWS_PER_STRATEGY

    return int(MAX_SNAPSHOT_ROWS_PER_STRATEGY)


def disk_refs_summary_for_row(row: Dict[str, Any]) -> Dict[str, List[str]]:
    """从一行快照的 ``result_report`` 提取磁盘目录引用摘要（仅日志用）。"""
    rr = dict((row or {}).get("result_report") or {})
    refs = _protected_dirs_from_result_report(rr)
    return {k: sorted(v) for k, v in refs.items() if v}


def log_workbench_version_deleted(strategy_name: str, version: int, row: Optional[Dict[str, Any]]) -> None:
    refs = disk_refs_summary_for_row(dict(row or {}))
    has_refs = any(refs.get(k) for k in ("enum", "price", "capital"))
    if has_refs:
        logger.info(
            "Deleted workbench version=%s strategy=%s; disk output_version refs in row were: %s "
            "(directories are not removed with the DB row)",
            version,
            strategy_name,
            refs,
        )
    else:
        logger.info(
            "Deleted workbench version=%s strategy=%s (no disk path refs in result_report)",
            version,
            strategy_name,
        )


class WorkbenchSnapshotRetention:
    """按 ``MAX_SNAPSHOT_ROWS_PER_STRATEGY`` 淘汰最早工作台快照行。"""

    def __init__(self, table_operator: Any) -> None:
        self._model = table_operator

    def prune_oldest_if_over_limit(self, strategy_name: str) -> None:
        model = self._model
        if model is None:
            return
        sn = str(strategy_name or "").strip()
        if not sn:
            return
        cap = _max_workbench_rows()
        rows = model.list_versions_asc(sn, limit=cap + 50)
        while len(rows) > cap:
            oldest = rows[0]
            sid = int((oldest or {}).get("version") or 0)
            if sid <= 0:
                break
            log_workbench_version_deleted(sn, sid, oldest)
            model.delete_version_row(sn, sid)
            rows = rows[1:]


def prune_workbench_rows_for_strategy(strategy_name: str) -> None:
    """维护入口：对单策略执行 DB 行数淘汰。"""
    model = DataManager().get_table("sys_strategy_workbench_snapshot")
    if model is None:
        return
    WorkbenchSnapshotRetention(model).prune_oldest_if_over_limit(strategy_name)


__all__ = [
    "WorkbenchSnapshotRetention",
    "disk_refs_summary_for_row",
    "log_workbench_version_deleted",
    "prune_workbench_rows_for_strategy",
]
