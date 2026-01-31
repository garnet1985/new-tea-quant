"""
Stock List Handler 配置。绑定表 sys_stock_list。
"""
CONFIG = {
    "table": "sys_stock_list",
    "renew": {
        "type": "refresh",
    },
    "apis": {
        "stock_list_data": {
            "provider_name": "tushare",
            "method": "get_stock_list",
            "max_per_minute": 10,
            "field_mapping": {
                "id": "ts_code",
                "name": "name",
                "industry_id": "industry",
                "market_id": "market",
            },
            "params": {
                "fields": "ts_code,symbol,name,area,industry,market,exchange,list_date",
            },
        },
    },
}
