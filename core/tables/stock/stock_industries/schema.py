"""
data_stock_industries 表结构定义（Python，变量名 schema）

股票–行业映射表：stock_id、industry_id。在 stock list renew 时与 data_industries 一并填充。
主键 stock_id、industry_id nullable=false。
"""
schema = {
    "name": "sys_stock_industries",
    "primaryKey": ["stock_id", "industry_id"],
    "fields": [
        {
            "name": "stock_id",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "股票代码",
        },
        {
            "name": "industry_id",
            "type": "int",
            "isRequired": True,
            "nullable": False,
            "description": "行业 id，关联 data_industries.id",
        },
    ],
    "indexes": [
        {"name": "idx_stock_industry", "fields": ["stock_id", "industry_id"], "unique": True},
        {"name": "idx_stock_id", "fields": ["stock_id"]},
        {"name": "idx_industry_id", "fields": ["industry_id"]},
    ],
}
