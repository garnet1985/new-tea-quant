"""
股票-地域映射表（sys_stock_area_map）：stock_id、area_id。
一只股票对应一个地域；与 sys_areas 配合，与 sys_stock_list 解耦。
主键 (stock_id, area_id)。
"""
schema = {
    "storage_domain": "data",  # 市场/宏观/股票主数据等（data 域）
    "update_key": "stock_stock_area_map",
    "name": "sys_stock_area_map",
    "primaryKey": ["stock_id", "area_id"],
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
            "name": "area_id",
            "type": "int",
            "isRequired": True,
            "nullable": False,
            "description": "地域 id，关联 sys_areas.id",
        },
    ],
    "indexes": [
        {"name": "idx_stock_id", "fields": ["stock_id"]},
        {"name": "idx_area_id", "fields": ["area_id"]},
    ],
}
