"""
股票-市场映射表（sys_stock_market_map）：stock_id、market_id。
一只股票对应一个市场；与 sys_markets 配合，与 sys_stock_list 解耦。
主键 (stock_id, market_id)。
"""
schema = {
    "name": "sys_stock_market_map",
    "primaryKey": ["stock_id", "market_id"],
    "fields": [
        {
            "name": "stock_id",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "股票代码，关联 sys_stock_list.id",
        },
        {
            "name": "market_id",
            "type": "int",
            "isRequired": True,
            "nullable": False,
            "description": "市场 id，关联 sys_markets.id",
        },
    ],
    "indexes": [
        {"name": "idx_stock_id", "fields": ["stock_id"]},
        {"name": "idx_market_id", "fields": ["market_id"]},
    ],
}
