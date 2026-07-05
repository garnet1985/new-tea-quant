"""MacroGdp DataKey 定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .loader import MacroGdpLoader
from core.modules.data_contract.core.data_keys.base_data_key import BaseDataKey
from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


@dataclass
class MacroGdpDataKey(BaseDataKey):
    """宏观 GDP DataKey。"""
    key: str = 'macro.gdp'
    scope: str = 'global'
    type: str = 'time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['quarter'])
    display_name: str = '宏观 GDP'
    time_axis_field: str = 'quarter'
    time_axis_format: str = 'YYYYQ'
    loader: Type[BaseDataKeyLoader] = MacroGdpLoader


# 默认实例
MACRO_GDP_DATA_KEY = MacroGdpDataKey()


__all__ = ['MACRO_GDP_DATA_KEY']