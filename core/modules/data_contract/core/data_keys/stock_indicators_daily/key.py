"""StockIndicatorsDaily DataKey 定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .loader import StockIndicatorsDailyLoader
from core.modules.data_contract.core.data_keys.base_data_key import BaseDataKey
from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


@dataclass
class StockIndicatorsDailyDataKey(BaseDataKey):
    """股票日频指标（PE/PB/市值）DataKey。"""
    key: str = 'stock.indicators.daily'
    scope: str = 'per_entity'
    type: str = 'time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['id', 'date'])
    display_name: str = '股票日频指标（PE/PB/市值）'
    time_axis_field: str = 'date'
    time_axis_format: str = 'YYYYMMDD'
    entity_list_data_key: str = 'stock.list'
    loader: Type[BaseDataKeyLoader] = StockIndicatorsDailyLoader


# 默认实例
STOCK_INDICATORS_DAILY_DATA_KEY = StockIndicatorsDailyDataKey()


__all__ = ['STOCK_INDICATORS_DAILY_DATA_KEY']