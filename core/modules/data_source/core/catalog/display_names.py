"""Default Chinese display names for built-in data source keys."""

from __future__ import annotations

from typing import Dict

DEFAULT_DISPLAY_NAMES: Dict[str, str] = {
    "stock_list": "股票列表",
    "boards": "板块定义",
    "markets": "交易所定义",
    "areas": "地域定义",
    "stock_board": "股票-板块映射",
    "stock_market": "股票-交易所映射",
    "stock_area": "股票-地域映射",
    "stock_klines": "股票 K 线",
    "stock_indicators": "股票日频指标",
    "stock_moneyflow": "个股资金流向",
    "corporate_finance": "公司财报",
    "stock_st_periods": "股票 ST 时段",
    "trade_calendar": "交易日历",
    "adj_factor_event": "复权因子事件",
    "sw_industry": "申万行业分类",
    "sw_stock_industry": "申万行业成分",
    "sw_industry_kline": "申万一级行业日线",
    "index_klines": "指数 K 线",
    "index_weight": "指数成分权重",
    "gdp": "宏观 GDP",
    "cpi": "宏观 CPI",
    "ppi": "宏观 PPI",
    "pmi": "宏观 PMI",
    "money_supply": "货币供应量",
    "shibor": "Shibor 利率",
    "lpr": "宏观 LPR",
    "ntq": "官网行情",
}
