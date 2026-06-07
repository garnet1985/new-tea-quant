"""
行业定义表（sys_industries）：id、value（行业名）、is_alive。
与 sys_stock_industry_map 配合；行业关系由映射表维护。
主键 id nullable=false；其余 nullable=true。
"""
schema = {
    "storage_domain": "data",  # 市场/宏观/股票主数据等（data 域）
    "update_key": "stock_industries",
    "name": "sys_industries",
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
            "description": "行业名称",
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
        {"name": "idx_is_alive", "fields": ["is_alive"]},
    ],
}
