"""
LPR Handler 配置。绑定表 sys_lpr。
"""
CONFIG = {
    "table": "sys_lpr",
    "renew": {
        "type": "rolling",
        "rolling": {
            "length": 30,
            "unit": "daily",
        },
        "last_update_info": {
            "date_field": "date",
            "date_format": "daily",
            "table_name": "sys_lpr",
        },
    },
    "apis": {
        "lpr_data": {
            "provider_name": "tushare",
            "method": "get_lpr",
            "max_per_minute": 10,
            "field_mapping": {
                "date": "date",
                "lpr_1_y": "1y",
                "lpr_5_y": "5y",
            },
            "params": {},
        },
    },
}
