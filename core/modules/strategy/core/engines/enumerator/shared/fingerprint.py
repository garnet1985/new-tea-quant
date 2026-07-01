"""枚举指纹与 execution_mode 解析。"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from core.modules.strategy.core.services.settings.settings_merge import StrategySettingsMerge


class EnumeratorExecutionMode:
    """settings → BacktestEngine 模式名。"""

    ENTITY_BASED = "entity_based"
    SLICE_BASED = "slice_based"

    _LEGACY_ALIASES = {
        "entity_timeline": ENTITY_BASED,
        "calendar_slice": SLICE_BASED,
    }

    @classmethod
    def resolve(cls, settings: Dict[str, Any]) -> str:
        simulation = settings.get("simulation")
        if not isinstance(simulation, dict):
            return cls.ENTITY_BASED
        raw = str(simulation.get("execution_mode") or "").strip()
        if not raw:
            return cls.ENTITY_BASED
        if raw in (cls.ENTITY_BASED, cls.SLICE_BASED):
            return raw
        return cls._LEGACY_ALIASES.get(raw, cls.ENTITY_BASED)


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
