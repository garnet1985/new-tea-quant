"""
core.tables：core 层表名常量（sys_ 前缀）

- core 表：sys_ 前缀，定义在 core/tables/ 各子目录的 schema.py。
- userspace 表：cust_ 前缀，定义在 userspace/tables/。
get_table()、config 的 table_name 等应使用本模块常量（如 SYS_STOCK_LIST）。
"""
from typing import FrozenSet

# core 表名（sys_ 前缀）
SYS_STOCK_LIST = "sys_stock_list"
SYS_STOCK_KLINE_DAILY = "sys_stock_kline_daily"
SYS_STOCK_KLINE_WEEKLY = "sys_stock_kline_weekly"
SYS_STOCK_KLINE_MONTHLY = "sys_stock_kline_monthly"
SYS_STOCK_INDICATORS = "sys_stock_indicators"
SYS_CPI = "sys_cpi"
SYS_PPI = "sys_ppi"
SYS_PMI = "sys_pmi"
SYS_MONEY_SUPPLY = "sys_money_supply"
SYS_INDUSTRIES = "sys_industries"
SYS_STOCK_INDUSTRIES = "sys_stock_industries"
SYS_ADJ_FACTOR_EVENT = "sys_adj_factor_event"
SYS_CORPORATE_FINANCE = "sys_corporate_finance"
SYS_GDP = "sys_gdp"
SYS_LPR = "sys_lpr"
SYS_SHIBOR = "sys_shibor"
SYS_STOCK_INDEX_INDICATOR = "sys_stock_index_indicator"
SYS_STOCK_INDEX_INDICATOR_WEIGHT = "sys_stock_index_indicator_weight"
SYS_INVESTMENT_OPERATIONS = "sys_investment_operations"
SYS_INVESTMENT_TRADES = "sys_investment_trades"
SYS_CACHE = "sys_cache"
SYS_TAG_SCENARIO = "sys_tag_scenario"
SYS_TAG_DEFINITION = "sys_tag_definition"
SYS_TAG_VALUE = "sys_tag_value"
SYS_META_INFO = "sys_meta_info"

SYS_TABLE_NAMES: FrozenSet[str] = frozenset({
    SYS_STOCK_LIST,
    SYS_STOCK_KLINE_DAILY,
    SYS_STOCK_KLINE_WEEKLY,
    SYS_STOCK_KLINE_MONTHLY,
    SYS_STOCK_INDICATORS,
    SYS_CPI,
    SYS_PPI,
    SYS_PMI,
    SYS_MONEY_SUPPLY,
    SYS_INDUSTRIES,
    SYS_STOCK_INDUSTRIES,
    SYS_ADJ_FACTOR_EVENT,
    SYS_CORPORATE_FINANCE,
    SYS_GDP,
    SYS_LPR,
    SYS_SHIBOR,
    SYS_STOCK_INDEX_INDICATOR,
    SYS_STOCK_INDEX_INDICATOR_WEIGHT,
    SYS_INVESTMENT_OPERATIONS,
    SYS_INVESTMENT_TRADES,
    SYS_CACHE,
    SYS_TAG_SCENARIO,
    SYS_TAG_DEFINITION,
    SYS_TAG_VALUE,
    SYS_META_INFO,
})

__all__ = [
    "SYS_STOCK_LIST",
    "SYS_STOCK_KLINE_DAILY",
    "SYS_STOCK_KLINE_WEEKLY",
    "SYS_STOCK_KLINE_MONTHLY",
    "SYS_STOCK_INDICATORS",
    "SYS_CPI",
    "SYS_PPI",
    "SYS_PMI",
    "SYS_MONEY_SUPPLY",
    "SYS_INDUSTRIES",
    "SYS_STOCK_INDUSTRIES",
    "SYS_ADJ_FACTOR_EVENT",
    "SYS_CORPORATE_FINANCE",
    "SYS_GDP",
    "SYS_LPR",
    "SYS_SHIBOR",
    "SYS_STOCK_INDEX_INDICATOR",
    "SYS_STOCK_INDEX_INDICATOR_WEIGHT",
    "SYS_INVESTMENT_OPERATIONS",
    "SYS_INVESTMENT_TRADES",
    "SYS_CACHE",
    "SYS_TAG_SCENARIO",
    "SYS_TAG_DEFINITION",
    "SYS_TAG_VALUE",
    "SYS_META_INFO",
    "SYS_TABLE_NAMES",
]
