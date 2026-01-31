"""
板块维度表（sys_stock_boards）：id、value（板块名）、is_alive。
在 stock list renew 时从 API 返回的 board 聚合填充（如主板、科创板、创业板、北交所）；stock_list 通过 board_id 关联。
主键 id nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_stock_boards",
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
            "description": "板块名称（如主板、科创板、创业板、北交所）",
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
