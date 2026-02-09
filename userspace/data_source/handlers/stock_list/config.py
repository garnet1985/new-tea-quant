"""
Stock List Handler 配置。绑定表 sys_stock_list。
行业/板块/市场由定义表 + 映射表维护；result_mapping 中的 industry/board/market 仅用于 handler 钩子解析后写入维度表与映射表，不写入 sys_stock_list（schema 无这些字段）。
"""
CONFIG = {
    "table": "sys_stock_list",
    "save_mode": "unified",
    "renew": {
        "type": "refresh",
    },
    "ignore_fields": ["is_active", "last_update"],
    "apis": {
        "stock_list_data": {
            "provider_name": "tushare",
            "method": "get_stock_list",
            "max_per_minute": 10,
            "result_mapping": {
                "id": "ts_code",
                "name": "name",
                "industry": "industry",
                "board": "market",
                "market": "exchange",
            },
            "params": {
                "fields": "ts_code,symbol,name,area,industry,market,exchange,list_date",
            },
        },
    },
}
