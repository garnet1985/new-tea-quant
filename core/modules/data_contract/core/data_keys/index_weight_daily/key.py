"""IndexWeightDaily DataKey 定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .loader import IndexWeightDailyLoader
from core.modules.data_contract.core.data_keys.base_data_key import BaseDataKey
from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


@dataclass
class IndexWeightDailyDataKey(BaseDataKey):
    """指数日频成分权重 DataKey。"""
    key: str = 'index.weight.daily'
    scope: str = 'per_entity'
    type: str = 'time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['id', 'date', 'stock_id'])
    display_name: str = '指数日频成分权重'
    time_axis_field: str = 'date'
    time_axis_format: str = 'YYYYMMDD'
    entity_list_data_key: str = 'index.list'
    loader: Type[BaseDataKeyLoader] = IndexWeightDailyLoader


# 默认实例
INDEX_WEIGHT_DAILY_DATA_KEY = IndexWeightDailyDataKey()


__all__ = ['INDEX_WEIGHT_DAILY_DATA_KEY']