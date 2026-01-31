"""
PPI Handler 配置。绑定表 sys_ppi。
"""
CONFIG = {
    "table": "sys_ppi",
    "renew": {
        "type": "rolling",
        "last_update_info": {
            "date_field": "date",
            "date_format": "monthly",
        },
        "rolling": {
            "unit": "monthly",
            "length": 12,
        },
    },
    "apis": {
        "ppi_data": {
            "provider_name": "tushare",
            "method": "get_ppi",
            "max_per_minute": 10,
            "field_mapping": {
                "date": "month",
                "ppi": "ppi_accu",
                "ppi_yoy": "ppi_yoy",
                "ppi_mom": "ppi_mom",
            },
            "params": {},
        },
    },
}
