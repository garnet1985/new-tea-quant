"""TAG DataKey 定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .loader import TagLoader
from core.modules.data_contract.core.data_keys.base_data_key import BaseDataKey
from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


@dataclass
class TagDataKey(BaseDataKey):
    """特征标签（按场景）DataKey。"""
    key: str = 'tag'
    scope: str = 'per_entity'
    type: str = 'time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['entity_id', 'tag_definition_id', 'as_of_date'])
    display_name: str = '特征标签（按场景）'
    time_axis_field: str = 'as_of_date'
    time_axis_format: str = 'YYYYMMDD'
    entity_list_data_key: str = 'stock.list'
    loader: Type[BaseDataKeyLoader] = TagLoader


# 默认实例
TAG_DATA_KEY = TagDataKey()


__all__ = ['TAG_DATA_KEY']