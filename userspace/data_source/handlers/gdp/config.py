"""
GDP Handler 配置。绑定表 sys_gdp。
"""
CONFIG = {
    "table": "sys_gdp",
    "renew": {
        "type": "rolling",
        "last_update_info": {
            "date_field": "quarter",
            "date_format": "quarterly",
            "table_name": "sys_gdp",
        },
        "rolling": {
            "unit": "quarterly",
            "length": 4,
        },
    },
    "apis": {
        "gdp_data": {
            "provider_name": "tushare",
            "method": "get_gdp",
            "max_per_minute": 200,
            "field_mapping": {
                "quarter": "quarter",
                "gdp": "gdp",
                "gdp_yoy": "gdp_yoy",
                "primary_industry": "pi",
                "primary_industry_yoy": "pi_yoy",
                "secondary_industry": "si",
                "secondary_industry_yoy": "si_yoy",
                "tertiary_industry": "ti",
                "tertiary_industry_yoy": "ti_yoy",
            },
            "params": {},
        },
    },
}
