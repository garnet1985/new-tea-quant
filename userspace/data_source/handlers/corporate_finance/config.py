"""
Corporate Finance Handler 配置。绑定表 sys_corporate_finance。
"""
from core.utils.date import DateUtils


CONFIG = {
    "table": "sys_corporate_finance",
    "renew": {
        "type": "rolling",
        "rolling": {
            "unit": DateUtils.PERIOD_QUARTER,
            "length": 3,
        },
        "last_update_info": {
            "date_field": "quarter",
            "date_format": DateUtils.PERIOD_QUARTER,
        },
        "result_group_by": {
            "list": "stock_list",
            "key": "id",
        },
    },
    "apis": {
        "finance_data": {
            "provider_name": "tushare",
            "method": "get_finance_data",
            "max_per_minute": 500,
            "group_by": "ts_code",
        },
    },
}
