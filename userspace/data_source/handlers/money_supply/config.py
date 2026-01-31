"""
Money Supply Handler 配置。绑定表 sys_money_supply。
"""
CONFIG = {
    "table": "sys_money_supply",
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
        "money_supply_data": {
            "provider_name": "tushare",
            "method": "get_money_supply",
            "max_per_minute": 10,
            "field_mapping": {
                "date": "month",
                "m0": "m0",
                "m0_yoy": "m0_yoy",
                "m0_mom": "m0_mom",
                "m1": "m1",
                "m1_yoy": "m1_yoy",
                "m1_mom": "m1_mom",
                "m2": "m2",
                "m2_yoy": "m2_yoy",
                "m2_mom": "m2_mom",
            },
            "params": {},
        },
    },
}
