#!/usr/bin/env python3
"""对外门面：指纹解析后读写快照表、按版本应用 settings、缓存清理与删除。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from core.modules.strategy.enums import Simulator

from .finger_print.finger_print import resolve_db_cache_fingerprints

if TYPE_CHECKING:
    from .cache_service import SimulatorResDbCacheService


class SimulatorResDbCacheWriteRequest:
    __slots__ = ("_service",)

    def __init__(self) -> None:
        self._service: SimulatorResDbCacheService | None = None

    @property
    def service(self) -> "SimulatorResDbCacheService":
        if self._service is None:
            from .cache_service import SimulatorResDbCacheService as _Svc

            self._service = _Svc()
        return self._service

    def load_cache_by_fingerprints(
        self,
        *,
        strategy_name: str,
        disk_settings: Dict[str, Any],
        user_modified_settings: Dict[str, Any],
        stock_ids: List[str],
        latest_completed_trading_date: str,
    ) -> Dict[str, Any]:
        resolved = resolve_db_cache_fingerprints(
            strategy_name=str(strategy_name),
            disk_settings=dict(disk_settings or {}),
            user_modified_settings=dict(user_modified_settings or {}),
            stock_list=list(stock_ids or []),
            latest_completed_trading_date=str(latest_completed_trading_date or "").strip(),
        )
        if resolved is None:
            return {}

        cache = self.service.load_cache_by_fingerprints(
            strategy_name=strategy_name,
            settings_fingerprint_id=resolved.settings_fp,
            env_fingerprint_id=resolved.env_fp,
        )

        if cache is None:
            return {}
        return cache

    def load_cache_by_version(self, strategy_name: str, version: int) -> Dict[str, Any]:
        return self.service.load_cache_by_version(strategy_name, version)

    def load_latest_cache_for_strategy(self, strategy_name: str,
    ) -> Dict[str, Any]:
        return self.service.load_latest_cache_for_strategy(strategy_name)

    def save_cache(
        self,
        *,
        strategy_name: str,
        disk_settings: Dict[str, Any],
        user_modified_settings: Dict[str, Any],
        simulator: Simulator,
        simulator_report: Dict[str, Any],
        stock_list: List[str],
        latest_completed_trading_date: str,
    ) -> int:
        """写入 DB 缓存。

        ``partial_result_report``：仅 **一种** 形状——本步摘要 dict，与 ``result_report`` 对应槽位将写入的 JSON 一致；无多形态兼容。
        """
        # Step 1 — settings_fp + env_fp（表列 ``settings_finger_print_id`` / ``env_fingerprint_id``）。
        resolved = resolve_db_cache_fingerprints(
            strategy_name=str(strategy_name),
            disk_settings=dict(disk_settings or {}),
            user_modified_settings=dict(user_modified_settings or {}),
            stock_list=stock_list,
            latest_completed_trading_date=str(latest_completed_trading_date or "").strip(),
        )
        if resolved is None:
            return 0

        try:
            return self.service.set_cache(
                strategy_name=strategy_name,
                settings_diff=resolved.settings_diff or {},  # 差异字段
                simulator=simulator,
                simulator_report=simulator_report or {},
                settings_fingerprint_id=resolved.settings_fp,
                env_fingerprint_id=resolved.env_fp,
            )
        except Exception:
            return 0

    def apply_strategy_settings_by_version(
        self,
        *,
        strategy_name: str,
        version: int,
    ) -> bool:
        from core.modules.strategy.services.cache.simulator_res_db_cache.finger_print.settings_diff import (
            merge_settings,
        )
        from core.modules.strategy.execution_manager.strategy_discovery import (
            load_strategy_info,
        )

        row = self.service.load_cache_by_version(
            strategy_name=strategy_name,
            version=version,
        )
        if not row:
            return False
        settings_diff = row.get("settings_snapshot")  # 数据库中存储的是差异字段
        if not isinstance(settings_diff, dict) or not settings_diff:
            return False

        # 读取磁盘上的 settings
        strategy_info = load_strategy_info(strategy_name)
        disk_settings = dict(strategy_info.settings.to_dict()) if strategy_info else {}

        # 合并差异字段和磁盘上的 settings
        merged_settings = merge_settings(disk_settings, settings_diff)

        self.service.backup_settings_file_for_strategy(strategy_name)
        self.service.write_settings_file_for_strategy(
            strategy_name,
            merged_settings,  # 合并后的完整 settings
            pretty=True,
        )
        return True

    def clean_up_cache(self):
        return self.service.clean_up_cache()

    def delete_cache_by_version(self, strategy_name: str, version: int) -> bool:
        return self.service.delete_cache_by_version(strategy_name, version)

    def delete_all_cache(self) -> int:
        return self.service.delete_all_cache()

    def delete_cache_for_strategy(self, strategy_name: str) -> bool:
        return self.service.delete_cache_for_strategy(strategy_name)