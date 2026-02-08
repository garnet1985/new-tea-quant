"""
Adj Factor Event Handler 配置。绑定表 sys_adj_factor_events。
"""
from core.utils.date import DateUtils


CONFIG = {
    "table": "sys_adj_factor_events",
    "save_mode": "batch",
    "save_batch_size": 20,
    "ignore_fields": ["id", "event_date", "factor", "qfq_diff", "last_update"],
    "renew": {
        "type": "incremental",
        "last_update_info": {
            "date_field": "event_date",
            "date_format": DateUtils.PERIOD_DAY,
        },
        "renew_if_over_days": {
            "value": 15,
            "counting_field": "last_update",
        },
        "job_execution": {
            "list": "stock_list",
            "key": "id",
        },
    },
    "apis": {
        "adj_factor": {
            "provider_name": "tushare",
            "method": "get_adj_factor",
            "max_per_minute": 800,
            "params_mapping": {
                "ts_code": "id",
            },
        },
        "daily_kline": {
            "provider_name": "tushare",
            "method": "get_daily_kline",
            "max_per_minute": 700,
            "params_mapping": {
                "ts_code": "id",
            },
        },
        "qfq_kline": {
            "provider_name": "eastmoney",
            "method": "get_qfq_kline",
            "max_per_minute": 60,
            "params_mapping": {
                "secid": "id",
            },
        },
    },
}
