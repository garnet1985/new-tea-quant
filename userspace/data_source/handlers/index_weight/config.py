"""
Index Weight Handler 配置。绑定表 sys_index_weight。
"""
from core.utils.date import DateUtils


CONFIG = {
    "table": "sys_index_weight",
    "save_mode": "batch",
    "save_batch_size": 20,
    "renew": {
        "type": "incremental",
        "last_update_info": {
            "date_field": "date",
            "date_format": DateUtils.PERIOD_DAY,
        },
        "renew_if_over_days": {
            "value": 30,
        },
        "job_execution": {
            "list": "index_list",
            "key": "id",
        },
    },
    "apis": {
        "index_weight": {
            "provider_name": "tushare",
            "method": "get_index_weight",
            "max_per_minute": 200,
            "params_mapping": {
                "index_code": "id",
            },
            "result_mapping": {
                "date": "trade_date",
                "stock_id": "con_code",
                "weight": "weight",
            },
            "params": {},
        },
    },
}
