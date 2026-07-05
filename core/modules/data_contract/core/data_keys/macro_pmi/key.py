"""MacroPmi DataKey 定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .loader import MacroPmiLoader
from core.modules.data_contract.core.data_keys.base_data_key import BaseDataKey
from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


@dataclass
class MacroPmiDataKey(BaseDataKey):
    """PMI（采购经理指数）DataKey。"""
    key: str = 'macro.pmi'
    scope: str = 'global'
    type: str = 'time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['date'])
    display_name: str = 'PMI（采购经理指数）'
    time_axis_field: str = 'date'
    time_axis_format: str = 'YYYYMMDD'
    loader: Type[BaseDataKeyLoader] = MacroPmiLoader


# 默认实例
MACRO_PMI_DATA_KEY = MacroPmiDataKey()


__all__ = ['MACRO_PMI_DATA_KEY']