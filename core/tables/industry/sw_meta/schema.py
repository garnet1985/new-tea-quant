"""
申万行业分类（sys_sw_industry）。

来自 Tushare index_classify(src=SW2021)。主键是指数代码（801010.SI）。
父子关系用 industry_code / parent_code，不用指数代码。
"""
schema = {
    "storage_domain": "data",
    "update_key": "stock_sw_industry",
    "name": "sys_sw_industry",
    "primaryKey": "id",
    "fields": [
        {
            "name": "id",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "申万指数代码，如 801010.SI",
        },
        {
            "name": "industry_code",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "申万行业代码，如 110000。parent_code 指向这个字段",
        },
        {
            "name": "name",
            "type": "varchar",
            "length": 64,
            "isRequired": True,
            "nullable": False,
            "description": "行业名称",
        },
        {
            "name": "level",
            "type": "varchar",
            "length": 8,
            "isRequired": True,
            "nullable": False,
            "description": "L1 / L2 / L3",
        },
        {
            "name": "parent_code",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "父级 industry_code。一级为 0",
        },
        {
            "name": "is_pub",
            "type": "tinyint",
            "isRequired": True,
            "nullable": False,
            "description": "是否发布指数行情 1/0。成分少于 5 只的三级通常为 0",
        },
        {
            "name": "src",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "分类版本，SW2021",
        },
    ],
    "indexes": [
        {"name": "idx_industry_code", "fields": ["industry_code"], "unique": True},
        {"name": "idx_level", "fields": ["level"]},
        {"name": "idx_parent_code", "fields": ["parent_code"]},
    ],
}
