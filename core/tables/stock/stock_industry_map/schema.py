"""
股票-行业映射表（sys_stock_industry_map）：stock_id、industry_id。
一只股票对应一个行业；与 sys_industries 配合，与 sys_stock_list 解耦。
主键 (stock_id, industry_id)。
"""
schema = {
    "name": "sys_stock_industry_map",
    "primaryKey": ["stock_id", "industry_id"],
    "fields": [
        {
            "name": "stock_id",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "股票代码，关联 sys_stock_list.id",
        },
        {
            "name": "industry_id",
            "type": "int",
            "isRequired": True,
            "nullable": False,
            "description": "行业 id，关联 sys_industries.id",
        },
    ],
    "indexes": [
        {"name": "idx_stock_id", "fields": ["stock_id"]},
        {"name": "idx_industry_id", "fields": ["industry_id"]},
    ],
}
