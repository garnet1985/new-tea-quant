"""Backward-compat shim — 逻辑已迁至 ``StrategySettings``。"""
from __future__ import annotations

from core.modules.strategy.core.data.settings.strategy_settings import StrategySettings


class StrategySettingsMerge:
    """Deprecated: use ``StrategySettings`` classmethods instead."""

    FINGERPRINT_FIELDS = StrategySettings.FINGERPRINT_FIELDS
    NON_FINGERPRINT_FIELDS = StrategySettings.NON_FINGERPRINT_FIELDS

    diff = staticmethod(StrategySettings.diff)
    filter_fingerprint_fields = staticmethod(StrategySettings._filter_fingerprint_fields)
    diff_for_fingerprint = staticmethod(StrategySettings.fingerprint_diff)
    merge = staticmethod(StrategySettings.merge_disk_with_diff)
    fingerprint_payload = staticmethod(StrategySettings.fingerprint_payload)


__all__ = ["StrategySettingsMerge"]
