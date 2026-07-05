"""Stock KLine DataKey 定义（daily/weekly/monthly）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .loader import StockKlineLoader
from core.modules.data_contract.core.data_keys.base_data_key import BaseDataKey
from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


@dataclass
class StockKlineDailyDataKey(BaseDataKey):
    """股票日 K 线 DataKey。"""
    key: str = 'stock.kline.daily'
    scope: str = 'per_entity'
    type: str = 'time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['date', 'stock_id'])
    display_name: str = '股票日 K 线'
    time_axis_field: str = 'date'
    time_axis_format: str = 'YYYYMMDD'
    entity_list_data_key: str = 'stock.list'
    loader: Type[BaseDataKeyLoader] = StockKlineLoader
    defaults: dict = field(default_factory=lambda: {'term': 'daily'})


@dataclass
class StockKlineWeeklyDataKey(BaseDataKey):
    """股票周 K 线 DataKey。"""
    key: str = 'stock.kline.weekly'
    scope: str = 'per_entity'
    type: str = 'time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['date', 'stock_id'])
    display_name: str = '股票周 K 线'
    time_axis_field: str = 'date'
    time_axis_format: str = 'YYYYMMDD'
    entity_list_data_key: str = 'stock.list'
    loader: Type[BaseDataKeyLoader] = StockKlineLoader
    defaults: dict = field(default_factory=lambda: {'term': 'weekly'})


@dataclass
class StockKlineMonthlyDataKey(BaseDataKey):
    """股票月 K 线 DataKey。"""
    key: str = 'stock.kline.monthly'
    scope: str = 'per_entity'
    type: str = 'time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['date', 'stock_id'])
    display_name: str = '股票月 K 线'
    time_axis_field: str = 'date'
    time_axis_format: str = 'YYYYMMDD'
    entity_list_data_key: str = 'stock.list'
    loader: Type[BaseDataKeyLoader] = StockKlineLoader
    defaults: dict = field(default_factory=lambda: {'term': 'monthly'})


# 默认实例
STOCK_KLINE_DAILY_DATA_KEY = StockKlineDailyDataKey()
STOCK_KLINE_WEEKLY_DATA_KEY = StockKlineWeeklyDataKey()
STOCK_KLINE_MONTHLY_DATA_KEY = StockKlineMonthlyDataKey()


__all__ = [
    'STOCK_KLINE_DAILY_DATA_KEY',
    'STOCK_KLINE_WEEKLY_DATA_KEY',
    'STOCK_KLINE_MONTHLY_DATA_KEY',
]