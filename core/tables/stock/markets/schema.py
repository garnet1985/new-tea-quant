"""
市场定义表（sys_markets）：id、value（交易所代码）、code、is_alive。
与 sys_stock_market_map 配合（Tushare exchange：SSE/SZSE/BSE）。
主键 id nullable=false；其余 nullable=true。
"""
schema = {
    "storage_domain": "data",  # 市场/宏观/股票主数据等（data 域）
    "update_key": "stock_markets",
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
            "description": "交易所代码（如 SSE、SZSE、BSE）",
        },
        {
            "name": "code",
            "type": "varchar",
            "length": 16,
            "isRequired": False,
            "nullable": True,
            "description": "与 value 相同的交易所代码（可选冗余）",
        },
        {
            "name": "is_alive",
            "type": "tinyint",
            "isRequired": True,
            "nullable": True,
            "description": "本批 stock_list 是否仍引用该字典项 1/0",
        },
    ],
    "indexes": [
        {"name": "idx_value", "fields": ["value"], "unique": True},
        {"name": "idx_code", "fields": ["code"], "unique": True},
        {"name": "idx_is_alive", "fields": ["is_alive"]},
    ],
}
