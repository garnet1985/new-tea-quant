"""
KlineHandler 配置。绑定表 sys_stock_klines。
"""
from core.utils.date import DateUtils


CONFIG = {
    "table": "sys_stock_klines",
    "renew": {
        "type": "incremental",
        "last_update_info": {
            "date_field": "date",
            "date_format": DateUtils.PERIOD_DAY,
        },
        "result_group_by": {
            "list": "stock_list",
            "by_key": "id",
        },
    },
    "apis": {
        "daily_kline": {
            "provider_name": "tushare",
            "method": "get_daily_kline",
            "max_per_minute": 700,
        },
        "weekly_kline": {
            "provider_name": "tushare",
            "method": "get_weekly_kline",
            "max_per_minute": 700,
        },
        "monthly_kline": {
            "provider_name": "tushare",
            "method": "get_monthly_kline",
            "max_per_minute": 700,
        },
    },
}
