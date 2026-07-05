"""StockAdjFactorEvents DataKey 定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .loader import StockAdjFactorEventsLoader
from core.modules.data_contract.core.data_keys.base_data_key import BaseDataKey
from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


@dataclass
class StockAdjFactorEventsDataKey(BaseDataKey):
    """股票复权因子事件 DataKey。"""
    key: str = 'stock.adj_factor.eventlog'
    scope: str = 'per_entity'
    type: str = 'time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['id', 'event_date'])
    display_name: str = '股票复权因子事件'
    time_axis_field: str = 'event_date'
    time_axis_format: str = 'YYYYMMDD'
    entity_list_data_key: str = 'stock.list'
    loader: Type[BaseDataKeyLoader] = StockAdjFactorEventsLoader


# 默认实例
STOCK_ADJ_FACTOR_EVENTS_DATA_KEY = StockAdjFactorEventsDataKey()


__all__ = ['STOCK_ADJ_FACTOR_EVENTS_DATA_KEY']