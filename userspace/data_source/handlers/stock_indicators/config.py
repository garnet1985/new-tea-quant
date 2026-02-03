"""
Stock Indicators Handler 配置。绑定表 sys_stock_indicators（原 daily_basic 数据）。
"""
from core.utils.date import DateUtils


CONFIG = {
    "table": "sys_stock_indicators",
    "renew": {
        "type": "incremental",
        "last_update_info": {
            "date_field": "date",
            "date_format": DateUtils.PERIOD_DAY,
        },
        "result_group_by": {
            "list": "stock_list",
            "key": "id",
        },
    },
    "apis": {
        "daily_basic": {
            "provider_name": "tushare",
            "method": "get_daily_basic",
            "max_per_minute": 700,
            "field_mapping": {
                "id": "ts_code",
                "date": "trade_date",
                "turnover_rate": "turnover_rate",
                "free_turnover_rate": "turnover_rate_f",
                "volume_ratio": "volume_ratio",
                "pe": "pe",
                "pe_ttm": "pe_ttm",
                "pb": "pb",
                "ps": "ps",
                "ps_ttm": "ps_ttm",
                "dv_ratio": "dv_ratio",
                "dv_ttm": "dv_ttm",
                "total_share": "total_share",
                "float_share": "float_share",
                "free_share": "free_share",
                "total_market_value": "total_mv",
                "circ_market_value": "circ_mv",
            },
            "params": {},
        },
    },
}
