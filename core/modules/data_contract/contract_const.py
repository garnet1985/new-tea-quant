from __future__ import annotations

from enum import Enum


class DataKey(str, Enum):
    """Data key identifiers."""

    STOCK_LIST = 'stock.list'
    STOCK_KLINE_DAILY_QFQ = 'stock.kline.daily.qfq'
    STOCK_KLINE_DAILY_NFQ = 'stock.kline.daily.nfq'
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
