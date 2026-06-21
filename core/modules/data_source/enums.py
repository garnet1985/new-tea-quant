"""数据源 renew / 日期窗口相关枚举。"""
from __future__ import annotations

from enum import Enum


class TermType(Enum):
    """周期类型（K 线 term、rolling 粒度等）。"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class UpdateMode(Enum):
    """数据更新模式（handler renew 配置）。"""

    INCREMENTAL = "incremental"
    REFRESH = "refresh"
    ROLLING = "rolling"

    @classmethod
    def from_string(cls, value: str) -> "UpdateMode":
        if value is None:
            raise ValueError("renew type 未配置")
        v = str(value).strip().lower()
        for mode in cls:
            if mode.value == v:
                return mode
        raise ValueError(f"无效的 renew 模式: {value!r}，应为 incremental | refresh | rolling")


__all__ = ["TermType", "UpdateMode"]
