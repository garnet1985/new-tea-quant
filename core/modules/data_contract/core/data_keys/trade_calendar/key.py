"""TradeCalendar DataKey 定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .loader import TradeCalendarLoader
from core.modules.data_contract.core.data_keys.base_data_key import BaseDataKey
from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


@dataclass
class TradeCalendarDataKey(BaseDataKey):
    """交易日历 DataKey。"""
    key: str = 'trade.calendar'
    scope: str = 'global'
    type: str = 'time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['date'])
    display_name: str = '交易日历'
    time_axis_field: str = 'date'
    time_axis_format: str = 'YYYYMMDD'
    loader: Type[BaseDataKeyLoader] = TradeCalendarLoader


# 默认实例
TRADE_CALENDAR_DATA_KEY = TradeCalendarDataKey()


__all__ = ['TRADE_CALENDAR_DATA_KEY']