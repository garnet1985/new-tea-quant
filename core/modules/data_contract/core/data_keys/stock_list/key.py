"""STOCK_LIST DataKey 定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .loader import StockListLoader
from core.modules.data_contract.core.data_keys.base_data_key import BaseDataKey
from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


@dataclass
class StockListDataKey(BaseDataKey):
    """STOCK_LIST DataKey。"""
    key: str = 'stock.list'
    scope: str = 'global'
    type: str = 'non_time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['id'])
    display_name: str = '股票列表'
    loader: Type[BaseDataKeyLoader] = StockListLoader


# 默认实例（方便直接使用）
STOCK_LIST_DATA_KEY = StockListDataKey()


__all__ = ['STOCK_LIST_DATA_KEY']