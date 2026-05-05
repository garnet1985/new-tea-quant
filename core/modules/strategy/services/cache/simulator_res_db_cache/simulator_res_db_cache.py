#!/usr/bin/env python3
"""对外入口：读缓存、写缓存、应用缓存（apply 待实现）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from core.modules.strategy.enums import Simulator

from .cache_service import SimulatorResDbCacheService
from .finger_print.finger_print import resolve_db_cache_fingerprints

class SimulatorResDbCacheWriteRequest:

    def __init__(self):
        self.service = SimulatorResDbCacheService()

    def load_cache_by_fingerprints(
        self,
        *,
        strategy_name: str,
        raw_settings: Dict[str, Any],
        stock_ids: List[str],
        latest_completed_trading_date: str,
    ) -> Dict[str, Any]:
        resolved = resolve_db_cache_fingerprints(
            strategy_name=str(strategy_name),
            raw_settings=dict(raw_settings or {}),
            stock_ids=list(stock_ids or []),
            latest_completed_trading_date=str(latest_completed_trading_date or "").strip(),
        )
        if resolved is None:
            return {}

        cache = self.service.get_cache_by_fingerprints(
            strategy_name=strategy_name,
            settings_fingerprint_id=resolved.settings_fp,
            env_fingerprint_id=resolved.env_fp,
        )

        if cache is None:
            return {}
        return cache

    def load_cache_by_version(self, strategy_name: str, version: int) -> Dict[str, Any]:
        return self.service.get_cache_by_version(
            strategy_name=strategy_name,
            version=version,
        )

    def load_latest_cache_for_strategy(self, strategy_name: str,
    ) -> Dict[str, Any]:
        return self.service.get_latest_cache_for_strategy(
            strategy_name=strategy_name,
        )

    def save_cache(
        self,
        *,
        strategy_name: str,
        raw_settings: Dict[str, Any],
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
            raw_settings=dict(raw_settings or {}),
            stock_list=stock_list,
            latest_completed_trading_date=str(latest_completed_trading_date or "").strip(),
        )
        if resolved is None:
            return 0

        try:
            self.service.set_cache(
                strategy_name=strategy_name,
                settings_snapshot=resolved.normalized_settings_dict or {},
                result_report=simulator_report or {},
                settings_fingerprint_id=resolved.settings_fp,
                env_fingerprint_id=resolved.env_fp,
            )
            return 1
        except Exception:
            return 0

    def apply_strategy_settings_by_version(
        self,
        *,
        strategy_name: str,
        version: int,
    ) -> bool:

        settings = self.service.load_cache_by_version(
            strategy_name=strategy_name,
            version=version,
        )

        if settings is None:
            return False

        self.service.backup_settings_file_for_strategy(strategy_name)

        self.service.write_settings_file_for_strategy(strategy_name, settings, pretty=True)

        return True

    def clean_up_cache(self):
        return self.service.clean_up_cache()

    def delete_cache_by_version(self, strategy_name: str, version: int) -> bool:
        return self.service.delete_cache_by_version(strategy_name, version)

    def delete_cache_for_strategy(self, strategy_name: str) -> bool:
        return self.service.delete_cache_for_strategy(strategy_name)