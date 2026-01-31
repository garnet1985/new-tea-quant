"""
市场定义表（sys_markets）：id、value（市场名）、is_alive。
如上海、深圳、北京。与 sys_stock_market_map 配合，stock_list 不再挂 market_id。
主键 id nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_markets",
    "primaryKey": "id",
    "fields": [
        {
            "name": "id",
            "type": "int",
            "isRequired": True,
            "nullable": False,
            "autoIncrement": True,
            "description": "主键自增",
        },
        {
            "name": "value",
            "type": "varchar",
            "length": 64,
            "isRequired": True,
            "nullable": True,
            "description": "市场名称（如沪市、深市）",
        },
        {
            "name": "code",
            "type": "varchar",
            "length": 16,
            "isRequired": False,
            "nullable": True,
            "description": "交易所代码（如 SSE/SZSE/BSE），与 value 对应",
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
        {"name": "idx_code", "fields": ["code"], "unique": True},
        {"name": "idx_is_alive", "fields": ["is_alive"]},
    ],
}
