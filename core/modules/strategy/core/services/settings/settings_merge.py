"""Strategy settings diff / merge（影响回测结果的字段参与指纹与持久化）。"""
from __future__ import annotations

import copy
from typing import Any, Dict, FrozenSet

from core.utils.utils import Utils


class StrategySettingsMerge:
    """磁盘基准 settings 与用户修改 diff 的合并与指纹字段筛选。"""

    FINGERPRINT_FIELDS: FrozenSet[str] = frozenset(
        {
            "core",
            "data",
            "goal",
            "sampling",
            "price_simulator",
            "capital_simulator",
            "fees",
            "simulation",
            "market_profile",
        }
    )

    NON_FINGERPRINT_FIELDS: FrozenSet[str] = frozenset(
        {
            "meta",
            "is_enabled",
            "scanner",
            "enumerator",
        }
    )

    @classmethod
    def diff(cls, disk_settings: Dict[str, Any], user_settings: Dict[str, Any]) -> Dict[str, Any]:
        """磁盘 vs 用户的完整 diff。"""
        return Utils.deep_diff(disk_settings, user_settings)

    @classmethod
    def filter_fingerprint_fields(cls, diff: Dict[str, Any]) -> Dict[str, Any]:
        """只保留影响回测结果的 diff 字段。"""
        return {
            key: copy.deepcopy(value)
            for key, value in diff.items()
            if key.split(".")[0] in cls.FINGERPRINT_FIELDS
        }

    @classmethod
    def diff_for_fingerprint(
        cls,
        disk_settings: Dict[str, Any],
        user_settings: Dict[str, Any],
    ) -> Dict[str, Any]:
        """diff + 指纹字段筛选（入库 / 缓存用）。"""
        return cls.filter_fingerprint_fields(cls.diff(disk_settings, user_settings))

    @classmethod
    def merge(cls, disk_settings: Dict[str, Any], settings_diff: Dict[str, Any]) -> Dict[str, Any]:
        """磁盘基准 + diff → 用户有效 settings。"""
        if not settings_diff:
            return copy.deepcopy(disk_settings)
        return Utils.deep_merge(copy.deepcopy(disk_settings), settings_diff)

    @classmethod
    def fingerprint_payload(cls, settings_diff: Dict[str, Any]) -> Dict[str, Any]:
        """用于指纹计算的 settings 片段（diff 即指纹字段集合）。"""
        return copy.deepcopy(settings_diff)


__all__ = ["StrategySettingsMerge"]
