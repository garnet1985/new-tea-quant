"""
股票列表（sys_stock_list）：仅基本信息；行业/板块/市场由定义表 + 映射表维护。

与 sys_industries、sys_boards、sys_markets 及 sys_stock_industry_map、sys_stock_board_map、
sys_stock_market_map 解耦，本表不再包含 industry_id / market_id / board_id。

主键、时序列 nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_stock_list",
    "primaryKey": "id",
    "fields": [
        {
            "name": "id",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "股票代码ts_code",
        },
        {
            "name": "name",
            "type": "varchar",
            "length": 255,
            "isRequired": True,
            "nullable": True,
        },
        {
            "name": "is_active",
            "type": "tinyint",
            "isRequired": True,
            "nullable": True,
        },
        {
            "name": "last_update",
            "type": "datetime",
            "isRequired": True,
            "nullable": True,
        },
    ],
}
