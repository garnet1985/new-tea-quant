#!/usr/bin/env python3
"""
Simulator Res DB Cache：``SimulatorResDbCacheService`` 负责表行读写与 ``result_report`` 合并。

槽位 lookup / persist 见 ``snapshot_slot_adapters``（**禁止**在本模块再导出，避免与 ``snapshot_slot_adapters`` 循环依赖）。
指纹数学在 ``finger_print``。
"""

from __future__ import annotations

import pprint
from typing import Any, Dict

from core.modules.strategy.enums import Simulator

from .config import MAX_SNAPSHOT_ROWS_PER_STRATEGY
from core.modules.data_manager import DataManager
from core.infra.project_context.path_manager import PathManager
from core.ui.bff.shared.file_ops import atomic_write_text, backup_file


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
        返回 ``snapshot_id``（``version``），失败为 ``0``。
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

        rows = model.list_by_strategy_fingerprints(
            strategy_name=str(strategy_name),
            settings_finger_print_id=sfp,
            env_fingerprint_id=efp,
            limit=1,
        )
        merged: Dict[str, Any]
        if rows:
            sid = int((rows[0] or {}).get("snapshot_id") or 0)
            if sid <= 0:
                return 0
            merged = dict((rows[0] or {}).get("result_report") or {})
            merged[slot_key] = step
            model.update_result_report(
                strategy_name,
                sid,
                merged,
                settings_finger_print_id=sfp,
                env_fingerprint_id=efp,
            )
            self._prune_oldest_if_over_limit(str(strategy_name))
            return sid

        merged = {slot_key: step}
        created = model.create_snapshot(
            str(strategy_name),
            dict(settings_snapshot or {}),
            merged,
            settings_finger_print_id=sfp,
            env_fingerprint_id=efp,
        )
        sid = int((created or {}).get("snapshot_id") or 0)
        if sid > 0:
            self._prune_oldest_if_over_limit(str(strategy_name))
        return sid

    def _prune_oldest_if_over_limit(self, strategy_name: str) -> None:
        model = self.table_operator
        if model is None:
            return
        rows = model.list_versions_asc(strategy_name, limit=MAX_SNAPSHOT_ROWS_PER_STRATEGY + 50)
        while len(rows) > MAX_SNAPSHOT_ROWS_PER_STRATEGY:
            oldest = rows[0]
            sid = int((oldest or {}).get("snapshot_id") or (oldest or {}).get("version") or 0)
            if sid <= 0:
                break
            model.delete_snapshot_row(strategy_name, sid)
            rows = rows[1:]

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
        """按 ``strategy_name`` + ``version``（表列 ``version`` / 领域 snapshot_id）加载一行；无则 ``{}``。"""
        model = self.table_operator
        if model is None:
            return {}
        row = model.load_by_strategy_snapshot_id(str(strategy_name), int(version))
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
        for row in rows or []:
            name = row.get("strategy_name")
            if isinstance(name, str) and name.strip():
                self._prune_oldest_if_over_limit(name.strip())

    def delete_cache_by_version(self, strategy_name: str, version: int) -> bool:
        """删除 ``strategy_name`` + ``version``（snapshot_id）对应的一行。"""
        model = self.table_operator
        if model is None:
            return False
        model._ensure_table_ready()
        n = model.delete_snapshot_row(str(strategy_name), int(version))
        return int(n or 0) > 0

    def delete_cache_for_strategy(self, strategy_name: str) -> bool:
        """删除该策略下全部快照行。"""
        model = self.table_operator
        if model is None:
            return False
        model._ensure_table_ready()
        n = model.delete("strategy_name = %s", (str(strategy_name),))
        return int(n or 0) > 0


DbCacheService = SimulatorResDbCacheService

__all__ = [
    "DbCacheService",
    "SimulatorResDbCacheService",
]
