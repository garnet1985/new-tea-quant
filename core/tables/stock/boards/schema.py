"""
板块定义表（sys_boards）：id、value（板块名）、is_active。
如主板、科创板、创业板、北交所。与 sys_stock_board_map 配合，stock_list 不再挂 board_id。
主键 id nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_boards",
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
            "description": "板块名称（如主板、科创板、创业板、北交所）",
        },
        {
            "name": "is_active",
            "type": "tinyint",
            "isRequired": True,
            "nullable": True,
            "description": "是否有效 1/0",
        },
    ],
    "indexes": [
        {"name": "idx_value", "fields": ["value"], "unique": True},
        {"name": "idx_is_active", "fields": ["is_active"]},
    ],
}
