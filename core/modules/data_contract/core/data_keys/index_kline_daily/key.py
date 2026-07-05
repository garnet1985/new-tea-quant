"""IndexKlineDaily DataKey 定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .loader import IndexKlineDailyLoader
from core.modules.data_contract.core.data_keys.base_data_key import BaseDataKey
from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


@dataclass
class IndexKlineDailyDataKey(BaseDataKey):
    """指数日 K 线 DataKey。"""
    key: str = 'index.kline.daily'
    scope: str = 'per_entity'
    type: str = 'time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['id', 'term', 'date'])
    display_name: str = '指数日 K 线'
    time_axis_field: str = 'date'
    time_axis_format: str = 'YYYYMMDD'
    entity_list_data_key: str = 'index.list'
    loader: Type[BaseDataKeyLoader] = IndexKlineDailyLoader


# 默认实例
INDEX_KLINE_DAILY_DATA_KEY = IndexKlineDailyDataKey()


__all__ = ['INDEX_KLINE_DAILY_DATA_KEY']