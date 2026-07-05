"""IndexList DataKey 定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .loader import IndexListLoader
from core.modules.data_contract.core.data_keys.base_data_key import BaseDataKey
from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


@dataclass
class IndexListDataKey(BaseDataKey):
    """指数列表 DataKey。"""
    key: str = 'index.list'
    scope: str = 'global'
    type: str = 'non_time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['id'])
    display_name: str = '指数列表'
    loader: Type[BaseDataKeyLoader] = IndexListLoader


# 默认实例
INDEX_LIST_DATA_KEY = IndexListDataKey()


__all__ = ['INDEX_LIST_DATA_KEY']