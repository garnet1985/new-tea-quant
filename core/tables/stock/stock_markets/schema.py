"""
市场维度表（sys_stock_markets）：id、value（市场名）、is_alive。
在 stock list renew 时从 API 返回的 market 聚合填充；stock_list 通过 market_id 关联。
主键 id nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_stock_markets",
    "primaryKey": "id",
    "fields": [
        {
            "name": "id",
            "type": "int",
            "isRequired": True,
            "nullable": False,
            "description": "主键",
        },
        {
            "name": "value",
            "type": "varchar",
            "length": 64,
            "isRequired": True,
            "nullable": True,
            "description": "市场名称（如上海、深圳、北京）",
        },
        {
            "name": "is_alive",
            "type": "tinyint",
            "isRequired": True,
            "nullable": True,
            "description": "是否有效 1/0",
        },
    ],
    "indexes": [
        {"name": "idx_value", "fields": ["value"], "unique": True},
        {"name": "idx_is_alive", "fields": ["is_alive"]},
    ],
}
