"""
Adj Factor Event Handler 配置。绑定表 sys_adj_factor_events。
"""
CONFIG = {
    "table": "sys_adj_factor_events",
    "renew": {
        "type": "incremental",
        "last_update_info": {
            "date_field": "event_date",
            "date_format": "daily",
            "table_name": "sys_adj_factor_events",
        },
        "renew_if_over_days": {
            "value": 15,
            "counting_field": "last_update",
        },
        "result_group_by": {
            "list": "stock_list",
            "by_key": "id",
        },
    },
    "apis": {
        "adj_factor": {
            "provider_name": "tushare",
            "method": "get_adj_factor",
            "max_per_minute": 800,
        },
        "daily_kline": {
            "provider_name": "tushare",
            "method": "get_daily_kline",
            "max_per_minute": 700,
        },
        "qfq_kline": {
            "provider_name": "eastmoney",
            "method": "get_qfq_kline",
            "max_per_minute": 60,
        },
    },
}
