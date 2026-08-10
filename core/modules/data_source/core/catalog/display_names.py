"""Default Chinese display names for built-in data source keys."""

from __future__ import annotations

from typing import Dict

DEFAULT_DISPLAY_NAMES: Dict[str, str] = {
    "stock_list": "股票列表",
    "stock_klines": "股票 K 线",
    "stock_indicators": "股票日频指标",
    "stock_moneyflow": "个股资金流向",
    "corporate_finance": "公司财报",
    "stock_st_periods": "股票 ST 时段",
    "trade_calendar": "交易日历",
    "adj_factor_event": "复权因子事件",
    "index_klines": "指数 K 线",
    "index_weight": "指数成分权重",
    "gdp": "宏观 GDP",
    "cpi": "宏观 CPI",
    "ppi": "宏观 PPI",
    "pmi": "宏观 PMI",
    "money_supply": "货币供应量",
    "shibor": "Shibor 利率",
    "lpr": "宏观 LPR",
}
