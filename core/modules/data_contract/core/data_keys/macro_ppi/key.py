"""MacroPpi DataKey 定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .loader import MacroPpiLoader
from core.modules.data_contract.core.data_keys.base_data_key import BaseDataKey
from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


@dataclass
class MacroPpiDataKey(BaseDataKey):
    """宏观 PPI DataKey。"""
    key: str = 'macro.ppi'
    scope: str = 'global'
    type: str = 'time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['date'])
    display_name: str = '宏观 PPI'
    time_axis_field: str = 'date'
    time_axis_format: str = 'YYYYMM'
    loader: Type[BaseDataKeyLoader] = MacroPpiLoader


# 默认实例
MACRO_PPI_DATA_KEY = MacroPpiDataKey()


__all__ = ['MACRO_PPI_DATA_KEY']