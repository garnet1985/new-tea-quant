from __future__ import annotations

from enum import Enum


class DataKey(str, Enum):
    """Data key identifiers."""

    STOCK_LIST = 'stock.list'
    # 通用 K 线：复权、周期由 params.adjust / params.term 指定（与下方具体 key 二选一）
    STOCK_KLINE = 'stock.kline'
    TAG = 'tag'

    STOCK_ADJ_FACTOR_EVENTS = 'stock.adj_factor.eventlog'
    STOCK_CORPORATE_FINANCE = 'stock.finance.quarterly'
    INDEX_LIST = 'index.list'
    INDEX_KLINE_DAILY = 'index.kline.daily'
    INDEX_WEIGHT_DAILY = 'index.weight.daily'
    MACRO_GDP = 'macro.gdp'
    MACRO_LPR = 'macro.lpr'
    MACRO_CPI = 'macro.cpi'
    MACRO_PPI = 'macro.ppi'
    MACRO_PMI = 'macro.pmi'


class ContractScope(str, Enum):
    """Contract scope semantics."""

    GLOBAL = 'global'
    PER_ENTITY = 'per_entity'


class ContractType(str, Enum):
    """Contract template type."""

    TIME_SERIES = 'time_series'
    NON_TIME_SERIES = 'non_time_series'
