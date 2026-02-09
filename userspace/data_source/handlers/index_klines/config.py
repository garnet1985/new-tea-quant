"""
Index Klines Handler 配置。绑定表 sys_index_klines。

与 stock_klines 逻辑一致：按 (id, term) 分组，支持 daily/weekly/monthly 独立追踪。
"""
from core.utils.date import DateUtils


CONFIG = {
    "table": "sys_index_klines",
    "save_mode": "batch",
    "save_batch_size": 20,
    "ignore_fields": ["id", "term"],  # 由 handler 注入
    "renew": {
        "type": "incremental",
        "last_update_info": {
            "date_field": "date",
            "date_format": DateUtils.PERIOD_DAY,
        },
        "renew_if_over_days": {
            "value": 1,
        },
        "job_execution": {
            "list": "index_list",
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
            "method": "get_index_daily",
            "max_per_minute": 500,
            "params_mapping": {
                "ts_code": "id",
                "term": "term",
            },
            "result_mapping": {
                "date": "trade_date",
                "open": "open",
                "close": "close",
                "highest": "high",
                "lowest": "low",
                "pre_close": "pre_close",
                "price_change_delta": "change",
                "price_change_rate_delta": "pct_chg",
                "volume": "vol",
                "amount": "amount",
            },
            "params": {},
        },
        "weekly_kline": {
            "provider_name": "tushare",
            "method": "get_index_weekly",
            "max_per_minute": 500,
            "params_mapping": {
                "ts_code": "id",
                "term": "term",
            },
            "result_mapping": {
                "date": "trade_date",
                "open": "open",
                "close": "close",
                "highest": "high",
                "lowest": "low",
                "pre_close": "pre_close",
                "price_change_delta": "change",
                "price_change_rate_delta": "pct_chg",
                "volume": "vol",
                "amount": "amount",
            },
            "params": {},
        },
        "monthly_kline": {
            "provider_name": "tushare",
            "method": "get_index_monthly",
            "max_per_minute": 500,
            "params_mapping": {
                "ts_code": "id",
                "term": "term",
            },
            "result_mapping": {
                "date": "trade_date",
                "open": "open",
                "close": "close",
                "highest": "high",
                "lowest": "low",
                "pre_close": "pre_close",
                "price_change_delta": "change",
                "price_change_rate_delta": "pct_chg",
                "volume": "vol",
                "amount": "amount",
            },
            "params": {},
        },
    },
}
