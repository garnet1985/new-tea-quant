from __future__ import annotations

from enum import Enum
from typing import Any, Dict, TypedDict, Type



class SYSTEM_DATA_KEYS(Enum):
    """Data key identifiers with full specifications."""

    STOCK_LIST = {
        'key': 'stock.list',
        'scope': 'global',
        'type': 'non_time_series',
        'unique_keys': ['id'],
        'display_name': '股票列表',
    }

    STOCK_KLINE_DAILY = {
        'key': 'stock.kline.daily',
        'scope': 'per_entity',
        'type': 'time_series',
        'unique_keys': ['date', 'stock_id'],
        'time_axis_field': 'date',
        'time_axis_format': 'YYYYMMDD',
        'entity_list_data_key': 'stock.list',
        'display_name': '股票日 K 线',
        'defaults': {'term': 'daily'},
    }

    STOCK_KLINE_WEEKLY = {
        'key': 'stock.kline.weekly',
        'scope': 'per_entity',
        'type': 'time_series',
        'unique_keys': ['date', 'stock_id'],
        'time_axis_field': 'date',
        'time_axis_format': 'YYYYMMDD',
        'entity_list_data_key': 'stock.list',
        'display_name': '股票周 K 线',
        'defaults': {'term': 'weekly'},
    }

    STOCK_KLINE_MONTHLY = {
        'key': 'stock.kline.monthly',
        'scope': 'per_entity',
        'type': 'time_series',
        'unique_keys': ['date', 'stock_id'],
        'time_axis_field': 'date',
        'time_axis_format': 'YYYYMMDD',
        'entity_list_data_key': 'stock.list',
        'display_name': '股票月 K 线',
        'defaults': {'term': 'monthly'},
    }

    TAG = {
        'key': 'tag',
        'scope': 'per_entity',
        'type': 'time_series',
        'unique_keys': ['entity_id', 'tag_definition_id', 'as_of_date'],
        'time_axis_field': 'as_of_date',
        'time_axis_format': 'YYYYMMDD',
        'entity_list_data_key': 'stock.list',
        'display_name': '特征标签（按场景）',
    }

    STOCK_ADJ_FACTOR_EVENTS = {
        'key': 'stock.adj_factor.eventlog',
        'scope': 'per_entity',
        'type': 'time_series',
        'unique_keys': ['id', 'event_date'],
        'time_axis_field': 'event_date',
        'time_axis_format': 'YYYYMMDD',
        'entity_list_data_key': 'stock.list',
        'display_name': '股票复权因子事件',
    }

    STOCK_CORPORATE_FINANCE = {
        'key': 'stock.finance.quarterly',
        'scope': 'per_entity',
        'type': 'time_series',
        'unique_keys': ['id', 'quarter'],
        'time_axis_field': 'ann_date',
        'time_axis_format': 'YYYYMMDD',
        'entity_list_data_key': 'stock.list',
        'display_name': '公司财报（季频）',
    }

    STOCK_INDICATORS_DAILY = {
        'key': 'stock.indicators.daily',
        'scope': 'per_entity',
        'type': 'time_series',
        'unique_keys': ['id', 'date'],
        'time_axis_field': 'date',
        'time_axis_format': 'YYYYMMDD',
        'entity_list_data_key': 'stock.list',
        'display_name': '股票日频指标（PE/PB/市值）',
    }

    STOCK_MONEYFLOW_DAILY = {
        'key': 'stock.moneyflow.daily',
        'scope': 'per_entity',
        'type': 'time_series',
        'unique_keys': ['id', 'date'],
        'time_axis_field': 'date',
        'time_axis_format': 'YYYYMMDD',
        'entity_list_data_key': 'stock.list',
        'display_name': '个股日频资金流向',
    }

    INDEX_LIST = {
        'key': 'index.list',
        'scope': 'global',
        'type': 'non_time_series',
        'unique_keys': ['id'],
        'display_name': '指数列表',
    }

    INDEX_KLINE_DAILY = {
        'key': 'index.kline.daily',
        'scope': 'per_entity',
        'type': 'time_series',
        'unique_keys': ['id', 'term', 'date'],
        'time_axis_field': 'date',
        'time_axis_format': 'YYYYMMDD',
        'entity_list_data_key': 'index.list',
        'display_name': '指数日 K 线',
    }

    INDEX_WEIGHT_DAILY = {
        'key': 'index.weight.daily',
        'scope': 'per_entity',
        'type': 'time_series',
        'unique_keys': ['id', 'date', 'stock_id'],
        'time_axis_field': 'date',
        'time_axis_format': 'YYYYMMDD',
        'entity_list_data_key': 'index.list',
        'display_name': '指数日频成分权重',
    }

    MACRO_GDP = {
        'key': 'macro.gdp',
        'scope': 'global',
        'type': 'time_series',
        'unique_keys': ['quarter'],
        'time_axis_field': 'quarter',
        'time_axis_format': 'YYYYQ',
        'display_name': '宏观 GDP',
    }

    MACRO_LPR = {
        'key': 'macro.lpr',
        'scope': 'global',
        'type': 'time_series',
        'unique_keys': ['date'],
        'time_axis_field': 'date',
        'time_axis_format': 'YYYYMMDD',
        'display_name': '宏观 LPR',
    }

    MACRO_CPI = {
        'key': 'macro.cpi',
        'scope': 'global',
        'type': 'time_series',
        'unique_keys': ['date'],
        'time_axis_field': 'date',
        'time_axis_format': 'YYYYMM',
        'display_name': '宏观 CPI',
    }

    MACRO_PPI = {
        'key': 'macro.ppi',
        'scope': 'global',
        'type': 'time_series',
        'unique_keys': ['date'],
        'time_axis_field': 'date',
        'time_axis_format': 'YYYYMM',
        'display_name': '宏观 PPI',
    }

    MACRO_PMI = {
        'key': 'macro.pmi',
        'scope': 'global',
        'type': 'time_series',
        'unique_keys': ['date'],
        'time_axis_field': 'date',
        'time_axis_format': 'YYYYMMDD',
        'display_name': 'PMI（采购经理指数）',
    }

    TRADE_CALENDAR = {
        'key': 'trade.calendar',
        'scope': 'global',
        'type': 'time_series',
        'unique_keys': ['date'],
        'time_axis_field': 'date',
        'time_axis_format': 'YYYYMMDD',
        'display_name': '交易日历',
    }

    @property
    def key(self) -> str:
        """唯一标识符（如 'stock.list'）。"""
        return self.value.get('key', self.name.lower())

    @property
    def scope(self) -> str:
        """Scope: 'global' or 'per_entity'。"""
        return self.value.get('scope', 'per_entity')

    @property
    def type(self) -> str:
        """Type: 'time_series' or 'non_time_series'。"""
        return self.value.get('type', 'time_series')

    @property
    def unique_keys(self) -> list[str]:
        """唯一键字段。"""
        return self.value.get('unique_keys', [])

    @property
    def time_axis_field(self) -> str:
        """时间轴字段（仅 time_series）。"""
        return self.value.get('time_axis_field', '')

    @property
    def time_axis_format(self) -> str:
        """时间格式（如 'YYYYMMDD'）。"""
        return self.value.get('time_axis_format', '')

    @property
    def entity_list_data_key(self) -> str:
        """关联的 entity list（仅 per_entity）。"""
        return self.value.get('entity_list_data_key', '')

    @property
    def display_name(self) -> str:
        """显示名称。"""
        return self.value.get('display_name', self.key)

    @property
    def defaults(self) -> Dict[str, Any]:
        """默认参数。"""
        return self.value.get('defaults', {})

    def is_global(self) -> bool:
        """是否为 global scope。"""
        return self.scope == 'global'

    def is_per_entity(self) -> bool:
        """是否为 per_entity scope。"""
        return self.scope == 'per_entity'

    def is_time_series(self) -> bool:
        """是否为 time_series type。"""
        return self.type == 'time_series'


__all__ = ['DataKey', 'DataKeySpec']