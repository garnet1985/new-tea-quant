"""
CPI Handler 配置。绑定表 sys_cpi。
"""
CONFIG = {
    "table": "sys_cpi",
    "renew": {
        "type": "rolling",
        "last_update_info": {
            "date_field": "date",
            "date_format": "monthly",
            "table_name": "sys_cpi",
        },
        "rolling": {
            "unit": "monthly",
            "length": 12,
        },
    },
    "apis": {
        "cpi_data": {
            "provider_name": "tushare",
            "method": "get_cpi",
            "max_per_minute": 10,
            "field_mapping": {
                "date": "month",
                "cpi": "nt_val",
                "cpi_yoy": "nt_yoy",
                "cpi_mom": "nt_mom",
            },
            "params": {},
        },
    },
}
