"""
指数列表（sys_index_list）表结构定义。

主键 id；运行时由 IndexService.sync_list_from_config() 从 data.json 的 benchmark_stock_index_list 同步写入。
"""
schema = {
    "storage_domain": "data",  # 市场/宏观/股票主数据等（data 域）
    "update_key": "index_index_list",
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
