"""
统一的 K 线 Handler 配置。绑定表 sys_stock_klines。

包含 daily/weekly/monthly 三个周期的 API 配置。
"""
from core.utils.date import DateUtils


CONFIG = {
    "table": "sys_stock_klines",
    "save_mode": "batch",
    "save_batch_size": 100,
    "renew": {
        "type": "incremental",
        "last_update_info": {
            "date_field": "date",
            "date_format": DateUtils.PERIOD_DAY,
        },
        "job_execution": {
            "list": "stock_list",
            "keys": ["id", "term"],
            "terms": ["daily", "weekly", "monthly"],
            "merge": {
                "by": "id",
            },
        },
    },
    "apis": {
        "daily_kline": {
            "provider_name": "tushare",
            "method": "get_daily_kline",
            "max_per_minute": 700,
            "params_mapping": {
                "ts_code": "id",
                "term": "term",
            },
            "result_mapping": {
                "id": "ts_code",
                "date": "trade_date",
                "open": "open",
                "highest": "high",
                "lowest": "low",
                "close": "close",
                "pre_close": "pre_close",
                "price_change_delta": "change",
                "price_change_rate_delta": "pct_chg",
                "volume": "vol",
                "amount": "amount",
            },
        },
        "weekly_kline": {
            "provider_name": "tushare",
            "method": "get_weekly_kline",
            "max_per_minute": 700,
            "params_mapping": {
                "ts_code": "id",
                "term": "term",
            },
            "result_mapping": {
                "id": "ts_code",
                "date": "trade_date",
                "open": "open",
                "highest": "high",
                "lowest": "low",
                "close": "close",
                "pre_close": "pre_close",
                "price_change_delta": "change",
                "price_change_rate_delta": "pct_chg",
                "volume": "vol",
                "amount": "amount",
            },
        },
        "monthly_kline": {
            "provider_name": "tushare",
            "method": "get_monthly_kline",
            "max_per_minute": 700,
            "params_mapping": {
                "ts_code": "id",
                "term": "term",
            },
            "result_mapping": {
                "id": "ts_code",
                "date": "trade_date",
                "open": "open",
                "highest": "high",
                "lowest": "low",
                "close": "close",
                "pre_close": "pre_close",
                "price_change_delta": "change",
                "price_change_rate_delta": "pct_chg",
                "volume": "vol",
                "amount": "amount",
            },
        },
    },
}
