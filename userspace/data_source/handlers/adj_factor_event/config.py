"""
Adj Factor Event Handler 配置。绑定表 sys_adj_factor_events。
"""
from core.utils.date import DateUtils


CONFIG = {
    "table": "sys_adj_factor_events",
    "save_mode": "batch",  # 批量保存：累计 save_batch_size 个 bundle 后保存
    "save_batch_size": 20,  # 每20个bundle保存一次
    "ignore_fields": ["id", "event_date", "factor", "qfq_diff", "last_update"],  # 这些字段由 handler 手动计算和填充，不在 field_mapping 中
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
        "result_group_by": {
            "list": "stock_list",
            "key": "id",
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
