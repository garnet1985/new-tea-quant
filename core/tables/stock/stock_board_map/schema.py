"""
股票-板块映射表（sys_map_stock_board）：stock_id、board_id。
一只股票对应一个板块；与 sys_data_boards 配合，与 sys_data_stock_list 解耦。
主键 (stock_id, board_id)。
"""
schema = {
    "storage_domain": "data",  # 市场/宏观/股票主数据等（data 域）
    "update_key": "stock_stock_board_map",
    "kind": "map",
    "name": "sys_map_stock_board",
    "primaryKey": ["stock_id", "board_id"],
    "fields": [
        {
            "name": "stock_id",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "股票代码，关联 sys_data_stock_list.id",
        },
        {
            "name": "board_id",
            "type": "int",
            "isRequired": True,
            "nullable": False,
            "description": "板块 id，关联 sys_data_boards.id",
        },
    ],
    "indexes": [
        {"name": "idx_stock_id", "fields": ["stock_id"]},
        {"name": "idx_board_id", "fields": ["board_id"]},
    ],
}
