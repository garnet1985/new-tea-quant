"""StockCorporateFinance DataKey 定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .loader import StockCorporateFinanceLoader
from core.modules.data_contract.core.data_keys.base_data_key import BaseDataKey
from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader


@dataclass
class StockCorporateFinanceDataKey(BaseDataKey):
    """公司财报（季频）DataKey。"""
    key: str = 'stock.finance.quarterly'
    scope: str = 'per_entity'
    type: str = 'time_series'
    unique_keys: list[str] = field(default_factory=lambda: ['id', 'quarter'])
    display_name: str = '公司财报（季频）'
    time_axis_field: str = 'ann_date'
    time_axis_format: str = 'YYYYMMDD'
    entity_list_data_key: str = 'stock.list'
    loader: Type[BaseDataKeyLoader] = StockCorporateFinanceLoader


# 默认实例
STOCK_CORPORATE_FINANCE_DATA_KEY = StockCorporateFinanceDataKey()


__all__ = ['STOCK_CORPORATE_FINANCE_DATA_KEY']