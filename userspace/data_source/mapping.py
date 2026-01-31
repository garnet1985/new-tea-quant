"""
数据源 mapping 配置。定义各 data source 的 handler、启用状态与依赖。

约定：
- handler 必须为「模块.类名」格式（如 kline.KlineHandler），框架从 handlers/<模块>/handler.py 加载该类。
- depends_on: 需要先执行的数据源列表，执行顺序由框架拓扑排序。
"""
DATA_SOURCES = {
    "stock_list": {
        "handler": "stock_list.TushareStockListHandler",
        "is_enabled": True,
    },
    "latest_trading_date": {
        "handler": "latest_trading_date.LatestTradingDateHandler",
        "is_enabled": True,
    },
    "kline": {
        "handler": "kline.KlineHandler",
        "is_enabled": False,
        "depends_on": ["stock_list", "latest_trading_date"],
    },
    "stock_indicators": {
        "handler": "stock_indicators.StockIndicatorsHandler",
        "is_enabled": False,
        "depends_on": ["stock_list", "latest_trading_date"],
    },
    "corporate_finance": {
        "handler": "corporate_finance.CorporateFinanceHandler",
        "is_enabled": False,
        "depends_on": ["stock_list", "latest_trading_date"],
    },
    "adj_factor_event": {
        "handler": "adj_factor_event.AdjFactorEventHandler",
        "is_enabled": False,
        "depends_on": ["stock_list", "latest_trading_date"],
    },
    "index_klines": {
        "handler": "index_klines.IndexKlinesHandler",
        "is_enabled": False,
        "depends_on": ["latest_trading_date"],
    },
    "index_weight": {
        "handler": "index_weight.IndexWeightHandler",
        "is_enabled": False,
        "depends_on": ["latest_trading_date"],
    },
    "gdp": {
        "handler": "gdp.GdpHandler",
        "is_enabled": False,
        "depends_on": ["latest_trading_date"],
    },
    "cpi": {
        "handler": "cpi.CpiHandler",
        "is_enabled": False,
        "depends_on": ["latest_trading_date"],
    },
    "ppi": {
        "handler": "ppi.PpiHandler",
        "is_enabled": False,
        "depends_on": ["latest_trading_date"],
    },
    "pmi": {
        "handler": "pmi.PmiHandler",
        "is_enabled": False,
        "depends_on": ["latest_trading_date"],
    },
    "money_supply": {
        "handler": "money_supply.MoneySupplyHandler",
        "is_enabled": False,
        "depends_on": ["latest_trading_date"],
    },
    "shibor": {
        "handler": "shibor.ShiborHandler",
        "is_enabled": False,
        "depends_on": ["latest_trading_date"],
    },
    "lpr": {
        "handler": "lpr.LprHandler",
        "is_enabled": False,
        "depends_on": ["latest_trading_date"],
    },
}
