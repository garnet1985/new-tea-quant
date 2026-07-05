"""MacroCpi DataKey 定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .loader import MacroCpiLoader
from core.modules.data_contract.core.data_keys.base_data_key import BaseDataKey
from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


@dataclass
class MacroCpiDataKey(BaseDataKey):
    """宏观 CPI DataKey。"""
    key: str = 'macro.cpi'
    scope: str = 'global'
    type: str = 'time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['date'])
    display_name: str = '宏观 CPI'
    time_axis_field: str = 'date'
    time_axis_format: str = 'YYYYMM'
    loader: Type[BaseDataKeyLoader] = MacroCpiLoader


# 默认实例
MACRO_CPI_DATA_KEY = MacroCpiDataKey()


__all__ = ['MACRO_CPI_DATA_KEY']