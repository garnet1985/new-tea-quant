"""
Index Weight Handler 配置。绑定表 sys_index_weight。
"""
from core.utils.date import DateUtils


CONFIG = {
    "table": "sys_index_weight",
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
        "index_weight": {
            "provider_name": "tushare",
            "method": "get_index_weight",
            "max_per_minute": 200,
            "field_mapping": {
                "date": "trade_date",
                "stock_id": "con_code",
                "weight": "weight",
            },
            "params": {},
            "group_by": "index_code",
        },
    },
}
