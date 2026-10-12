"""
股票当前申万行业（sys_sw_stock_industry_map）。

一只股票一行，同时记下一级、二级、三级指数代码。
这是最新成分快照，in_date 不是行业变更历史。
"""
schema = {
    "storage_domain": "data",
    "update_key": "stock_sw_stock_industry_map",
    "name": "sys_sw_stock_industry_map",
    "primaryKey": "stock_id",
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
            "name": "l1_code",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "一级行业指数代码，关联 sys_sw_industry.id",
        },
        {
            "name": "l2_code",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "二级行业指数代码",
        },
        {
            "name": "l3_code",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "三级行业指数代码",
        },
        {
            "name": "in_date",
            "type": "varchar",
            "length": 8,
            "isRequired": False,
            "nullable": True,
            "description": "接口返回的纳入日。不能当作行业变更日志",
        },
    ],
    "indexes": [
        {"name": "idx_l1_code", "fields": ["l1_code"]},
        {"name": "idx_l2_code", "fields": ["l2_code"]},
        {"name": "idx_l3_code", "fields": ["l3_code"]},
    ],
}
