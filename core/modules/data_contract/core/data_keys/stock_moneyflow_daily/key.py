"""StockMoneyflowDaily DataKey 定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .loader import StockMoneyflowDailyLoader
from core.modules.data_contract.core.data_keys.base_data_key import BaseDataKey
from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


@dataclass
class StockMoneyflowDailyDataKey(BaseDataKey):
    """个股日频资金流向 DataKey。"""
    key: str = 'stock.moneyflow.daily'
    scope: str = 'per_entity'
    type: str = 'time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['id', 'date'])
    display_name: str = '个股日频资金流向'
    time_axis_field: str = 'date'
    time_axis_format: str = 'YYYYMMDD'
    entity_list_data_key: str = 'stock.list'
    loader: Type[BaseDataKeyLoader] = StockMoneyflowDailyLoader


# 默认实例
STOCK_MONEYFLOW_DAILY_DATA_KEY = StockMoneyflowDailyDataKey()


__all__ = ['STOCK_MONEYFLOW_DAILY_DATA_KEY']