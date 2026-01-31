"""
Price Indexes Handler 配置。绑定表 sys_cpi；PPI/PMI/Money Supply 由 handler 在 hooks 中写入对应表。
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
        "data_merging": {
            "merge_by_key": "date",
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
        "pmi_data": {
            "provider_name": "tushare",
            "method": "get_pmi",
            "max_per_minute": 10,
            "field_mapping": {
                "date": "MONTH",
                "pmi": "PMI010000",
                "pmi_l_scale": "PMI010100",
                "pmi_m_scale": "PMI010200",
                "pmi_s_scale": "PMI010300",
            },
            "params": {},
        },
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
