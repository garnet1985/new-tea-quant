#!/usr/bin/env python3
"""
Simulator Res DB Cache：``SimulatorResDbCacheService`` 负责表行读写与 ``result_report`` 合并。

槽位 lookup / persist 见 ``snapshot_slot_adapters``（**禁止**在本模块再导出，避免与 ``snapshot_slot_adapters`` 循环依赖）。
指纹数学在 ``finger_print``。
"""

from __future__ import annotations

import logging
import pprint
from typing import Any, Dict

from core.modules.strategy.enums import Simulator

from .audit.result_report_audit import (
    attach_initial_write_meta,
    bump_write_count,
)
from core.modules.data_manager import DataManager
from core.infra.project_context.path_manager import PathManager

logger = logging.getLogger(__name__)


def _resolve_cache_target_row(
    model,
    *,
    strategy_name: str,
    settings_fingerprint_id: str,
    env_fingerprint_id: str,
):
    """双指纹 AND 命中唯一快照行。"""
    sfp = str(settings_fingerprint_id or "").strip()
    efp = str(env_fingerprint_id or "").strip()
    sn = str(strategy_name).strip()
    rows = model.list_by_strategy_fingerprints(
        strategy_name=sn,
        settings_finger_print_id=sfp,
        env_fingerprint_id=efp,
        limit=1,
    )
    if rows:
        return rows[0] or {}
    return None


def _simulator_to_reports_slot_key(simulator: Simulator) -> str:
    if simulator == Simulator.ENUMERATOR:
        return "enum"
    if simulator == Simulator.PRICE_FACTOR:
        return "price_factor"
    if simulator == Simulator.CAPITAL_ALLOCATION:
        return "capital_allocation"
    raise ValueError(f"未知 simulator: {simulator!r}")


class SimulatorResDbCacheService:
    def __init__(self) -> None:
        data_mgr = DataManager()
        self.table_operator = data_mgr.get_table("sys_strategy_workbench_snapshot")
        self._row_retention = None

    def _retention(self):
        if self._row_retention is None:
            from core.modules.strategy.services.data.output.workbench_snapshot_retention import (
                WorkbenchSnapshotRetention,
            )

            self._row_retention = WorkbenchSnapshotRetention(self.table_operator)
        return self._row_retention

    def set_cache(
        self,
        strategy_name: str,
        settings_snapshot: Dict[str, Any],
        simulator: Simulator,
        simulator_report: Dict[str, Any],
        settings_fingerprint_id: str,
        env_fingerprint_id: str,
    ) -> int:
        """
        双指纹命中则合并更新 ``reports`` / ``result_report`` 聚合 JSON 中对应槽位；否则新建一行。
        返回工作台 ``version``，失败为 ``0``。
        """
        model = self.table_operator
        if model is None:
            return 0
        step = dict(simulator_report or {})
        if not step:
            return 0
        slot_key = _simulator_to_reports_slot_key(simulator)
        sfp = str(settings_fingerprint_id or "").strip()
        efp = str(env_fingerprint_id or "").strip()
        sn = str(strategy_name)

        row = _resolve_cache_target_row(
            model,
            strategy_name=sn,
            settings_fingerprint_id=sfp,
            env_fingerprint_id=efp,
        )
        if row:
            sid = int(row.get("version") or 0)
            if sid <= 0:
                return 0
            merged = dict(row.get("result_report") or {})
            merged[slot_key] = step
            merged, _ = bump_write_count(merged)
            model.update_result_report(
                sn,
                sid,
                merged,
                settings_finger_print_id=sfp,
                env_fingerprint_id=efp,
            )
            self._retention().prune_oldest_if_over_limit(sn)
            return sid

        merged = attach_initial_write_meta({slot_key: step})
        created = model.create_snapshot(
            sn,
            dict(settings_snapshot or {}),
            merged,
            settings_finger_print_id=sfp,
            env_fingerprint_id=efp,
        )
        sid = int((created or {}).get("version") or 0)
        if sid > 0:
            self._retention().prune_oldest_if_over_limit(sn)
        return sid

    def load_cache_by_fingerprints(
        self,
        strategy_name: str,
        settings_fingerprint_id: str,
        env_fingerprint_id: str,
    ) -> Dict[str, Any]:
        """双指纹 AND 命中最新一行；未命中或表未注册则 ``{}``。"""
        model = self.table_operator
        if model is None:
            return {}
        rows = model.list_by_strategy_fingerprints(
            strategy_name=str(strategy_name),
            settings_finger_print_id=str(settings_fingerprint_id or "").strip(),
            env_fingerprint_id=str(env_fingerprint_id or "").strip(),
            limit=1,
        )
        if not rows:
            return {}
        return dict(rows[0] or {})

    def load_cache_by_version(
        self,
        strategy_name: str,
        version: int,
    ) -> Dict[str, Any]:
        """按 ``strategy_name`` + 工作台 ``version`` 加载一行；无则 ``{}``。"""
        model = self.table_operator
        if model is None:
            return {}
        row = model.load_by_strategy_version(str(strategy_name), int(version))
        if not row:
            return {}
        return dict(row)

    def load_latest_cache_for_strategy(
        self,
        strategy_name: str,
    ) -> Dict[str, Any]:
        """按 ``strategy_name`` 取版本号最大的一行；无则 ``{}``。"""
        model = self.table_operator
        if model is None:
            return {}
        rows = model.list_by_strategy(str(strategy_name), limit=1)
        if not rows:
            return {}
        return dict(rows[0] or {})

    def backup_settings_file_for_strategy(self, strategy_name: str) -> None:
        """若存在 ``userspace/strategies/{name}/settings.py``，则备份为 ``settings.py.bak``。"""
        from core.ui.bff.shared.file_ops import backup_file

        settings_file = PathManager.strategy_settings(str(strategy_name))
        if settings_file.is_file():
            backup_file(settings_file)

    def write_settings_file_for_strategy(
        self,
        strategy_name: str,
        settings: Dict[str, Any],
        pretty: bool,
    ) -> None:
        """将 API 形态的 ``settings`` dict 写入 ``settings.py``（与 Workbench 写入风格一致）。"""
        from core.ui.bff.shared.file_ops import atomic_write_text

        settings_file = PathManager.strategy_settings(str(strategy_name))
        if pretty:
            literal = pprint.pformat(dict(settings or {}), width=100, sort_dicts=True)
        else:
            literal = repr(dict(settings or {}))
        content = (
            "# Auto-generated by DbCache (apply snapshot version to userspace).\n"
            "# Manual edits are allowed; next save from Workbench may reformat this file.\n\n"
            f"settings = {literal}\n"
        )
        atomic_write_text(settings_file, content)

    def clean_up_cache(self) -> None:
        """对快照表中出现的每个 ``strategy_name``，按 ``MAX_SNAPSHOT_ROWS_PER_STRATEGY`` 淘汰最早版本。"""
        model = self.table_operator
        if model is None:
            return
        model._ensure_table_ready()
        rows = model.execute_raw_query(
            f"SELECT DISTINCT strategy_name FROM {model.table_name}",
            (),
        )
        retention = self._retention()
        for row in rows or []:
            name = row.get("strategy_name")
            if isinstance(name, str) and name.strip():
                retention.prune_oldest_if_over_limit(name.strip())

    def delete_cache_by_version(self, strategy_name: str, version: int) -> bool:
        """删除 ``strategy_name`` + 工作台 ``version`` 对应的一行。"""
        model = self.table_operator
        if model is None:
            return False
        model._ensure_table_ready()
        sn = str(strategy_name).strip()
        sid = int(version)
        if not sn or sid <= 0:
            return False
        row = model.load_by_strategy_version(sn, sid)
        if not row:
            return False
        from core.modules.strategy.services.data.output.workbench_snapshot_retention import (
            log_workbench_version_deleted,
        )

        log_workbench_version_deleted(sn, sid, row)
        n = model.delete_version_row(sn, sid)
        return int(n or 0) > 0

    def delete_all_cache(self) -> int:
        """删除 ``sys_strategy_workbench_snapshot`` 表内全部快照行；**不**删除磁盘模拟产物。"""
        model = self.table_operator
        if model is None:
            return 0
        model._ensure_table_ready()
        from core.modules.strategy.services.data.output.workbench_snapshot_retention import (
            log_workbench_version_deleted,
        )

        rows = model.execute_raw_query(
            f"SELECT strategy_name, version FROM {model.table_name} "
            "ORDER BY strategy_name ASC, version ASC",
            (),
        )
        total = 0
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            sn = str(row.get("strategy_name") or "").strip()
            sid = int(row.get("version") or 0)
            if not sn or sid <= 0:
                continue
            full_row = model.load_by_strategy_version(sn, sid)
            if full_row:
                log_workbench_version_deleted(sn, sid, full_row)
            total += int(model.delete_version_row(sn, sid) or 0)
        return total

    def delete_cache_for_strategy(self, strategy_name: str) -> bool:
        """删除该策略下全部快照行。"""
        model = self.table_operator
        if model is None:
            return False
        model._ensure_table_ready()
        n = model.delete("strategy_name = %s", (str(strategy_name),))
        return int(n or 0) > 0


__all__ = [
    "SimulatorResDbCacheService",
]
