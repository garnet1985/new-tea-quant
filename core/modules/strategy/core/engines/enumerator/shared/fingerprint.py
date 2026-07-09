"""Backward-compat shims — 逻辑已迁至 ``StrategySettings``。"""
from __future__ import annotations

from typing import Any, Dict, List

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import StrategySettings


class EnumeratorExecutionMode:
    """Deprecated: use ``StrategySettings.execution_mode``."""

    ENTITY_BASED = "entity_based"
    SLICE_BASED = "slice_based"

    @classmethod
    def resolve(cls, settings: Dict[str, Any]) -> str:
        return StrategySettings(raw_settings=settings).execution_mode


class EnumeratorFingerprint:
    """Deprecated: use ``StrategySettings.fingerprint_hash``."""

    @classmethod
    def calculate_fingerprint_hash(
        cls,
        settings_diff: Dict[str, Any],
        entity_ids: List[str],
        start_date: str,
        end_date: str,
    ) -> str:
        return StrategySettings(raw_settings={}).fingerprint_hash(
            settings_diff=settings_diff,
            entity_ids=entity_ids,
            start_date=start_date,
            end_date=end_date,
        )


__all__ = ["EnumeratorExecutionMode", "EnumeratorFingerprint"]
