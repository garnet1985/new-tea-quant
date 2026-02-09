"""
指数列表（sys_index_list）表结构定义。

主键 id；data.json 为该表初始值（上证、沪深300、科创50、深证成指、创业板指等）。
"""
schema = {
    "name": "sys_index_list",
    "primaryKey": "id",
    "fields": [
        {
            "name": "id",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "指数代码，如 000001.SH、399006.SZ",
        },
        {
            "name": "name",
            "type": "varchar",
            "length": 64,
            "isRequired": True,
            "nullable": True,
            "description": "指数名称",
        },
        {
            "name": "description",
            "type": "text",
            "isRequired": False,
            "nullable": True,
            "description": "指数说明",
        },
        {
            "name": "type",
            "type": "varchar",
            "length": 16,
            "isRequired": False,
            "nullable": True,
            "description": "指数类型",
        },
    ],
    "indexes": [
        {"name": "idx_id", "fields": ["id"], "unique": True},
    ],
}
