"""
Index Klines Handler 配置。绑定表 sys_index_klines。
"""
from core.utils.date import DateUtils


CONFIG = {
    "table": "sys_index_klines",
    "save_mode": "batch",  # 批量保存：累计 save_batch_size 个 bundle 后保存
    "save_batch_size": 20,  # 每20个bundle保存一次
    "renew": {
        "type": "incremental",
        "last_update_info": {
            "date_field": "date",
            "date_format": DateUtils.PERIOD_DAY,
        },
        "renew_if_over_days": {
            "value": 30,
        },
        "result_group_by": {
            "list": "index_list",
            "key": "id",
        },
    },
    "apis": {
        "daily_kline": {
            "provider_name": "tushare",
            "method": "get_index_daily",
            "max_per_minute": 500,
            "field_mapping": {
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
            "field_mapping": {
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
            "field_mapping": {
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
