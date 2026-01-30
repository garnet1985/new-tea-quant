"""
data_industries 表结构定义（Python，变量名 schema）

行业维度表：id、value（行业名）、is_alive。在 stock list renew 时从 Tushare 返回的 industry 聚合填充。
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
            "description": "是否有效 1/0",
        },
    ],
    "indexes": [
        {"name": "idx_value", "fields": ["value"], "unique": True},
        {"name": "idx_is_alive", "fields": ["is_alive"]},
    ],
}
