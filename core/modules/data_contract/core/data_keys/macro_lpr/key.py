"""MacroLpr DataKey 定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .loader import MacroLprLoader
from core.modules.data_contract.core.data_keys.base_data_key import BaseDataKey
from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


@dataclass
class MacroLprDataKey(BaseDataKey):
    """宏观 LPR DataKey。"""
    key: str = 'macro.lpr'
    scope: str = 'global'
    type: str = 'time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['date'])
    display_name: str = '宏观 LPR'
    time_axis_field: str = 'date'
    time_axis_format: str = 'YYYYMMDD'
    loader: Type[BaseDataKeyLoader] = MacroLprLoader


# 默认实例
MACRO_LPR_DATA_KEY = MacroLprDataKey()


__all__ = ['MACRO_LPR_DATA_KEY']