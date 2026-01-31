"""
Stock List Handler 配置。绑定表 sys_stock_list。
行业/板块/市场由定义表 + 映射表维护，此处仅映射文本字段，保存前在 handler 内解析并写入维度表与映射表。
schema 以外的字段（如 industry/board/market）在 normalized 时会被自动忽略，无需 ignore_fields。
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
