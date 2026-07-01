"""枚举指纹与 execution_mode 解析。"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.strategy.core.services.settings.settings_merge import StrategySettingsMerge


class EnumeratorExecutionMode:
    """settings → BacktestEngine 模式名（与 BacktestMode 对齐）。"""

    ENTITY_BASED = BacktestMode.ENTITY_BASED.value
    SLICE_BASED = BacktestMode.SLICE_BASED.value

    @classmethod
    def resolve(cls, settings: Dict[str, Any]) -> str:
        simulation = settings.get("simulation")
        if not isinstance(simulation, dict):
            raise ValueError("settings.simulation 须为 dict")
        raw = simulation.get("execution_mode")
        if raw is None or str(raw).strip() == "":
            raise ValueError(
                f"settings.simulation.execution_mode 必填"
                f"（{BacktestMode.ENTITY_BASED.value} | {BacktestMode.SLICE_BASED.value}）"
            )
        return BacktestMode.normalize(raw)


class EnumeratorFingerprint:
    """枚举指纹（基于 settings_diff）。"""

    @staticmethod
    def _stable_hash(payload: Dict[str, Any]) -> str:
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def calculate_fingerprint_hash(
        cls,
        settings_diff: Dict[str, Any],
        entity_ids: List[str],
        start_date: str,
        end_date: str,
    ) -> str:
        signature = {
            "settings": StrategySettingsMerge.fingerprint_payload(settings_diff),
            "entity_ids": sorted(entity_ids),
            "start_date": start_date,
            "end_date": end_date,
        }
        return cls._stable_hash(signature)


__all__ = ["EnumeratorExecutionMode", "EnumeratorFingerprint"]
