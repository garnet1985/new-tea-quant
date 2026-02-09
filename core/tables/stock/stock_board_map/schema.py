"""
股票-板块映射表（sys_stock_board_map）：stock_id、board_id。
一只股票对应一个板块；与 sys_boards 配合，与 sys_stock_list 解耦。
主键 (stock_id, board_id)。
"""
schema = {
    "name": "sys_stock_board_map",
    "primaryKey": ["stock_id", "board_id"],
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
            "name": "board_id",
            "type": "int",
            "isRequired": True,
            "nullable": False,
            "description": "板块 id，关联 sys_boards.id",
        },
    ],
    "indexes": [
        {"name": "idx_stock_id", "fields": ["stock_id"]},
        {"name": "idx_board_id", "fields": ["board_id"]},
    ],
}
