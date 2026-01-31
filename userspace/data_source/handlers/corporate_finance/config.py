"""
Corporate Finance Handler 配置。绑定表 sys_corporate_finance。
"""
CONFIG = {
    "table": "sys_corporate_finance",
    "renew": {
        "type": "rolling",
        "rolling": {
            "unit": "quarterly",
            "length": 3,
        },
        "last_update_info": {
            "date_field": "quarter",
            "date_format": "quarterly",
            "table_name": "sys_corporate_finance",
        },
        "result_group_by": {
            "list": "stock_list",
            "by_key": "id",
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
