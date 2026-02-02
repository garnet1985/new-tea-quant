"""
行业定义表（sys_industries）：id、value（行业名）、is_active。
与 sys_stock_industry_map 配合，stock_list 不再挂 industry_id；行业关系由映射表维护。
主键 id nullable=false；其余 nullable=true。
"""
schema = {
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
