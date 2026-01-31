"""
股票列表（sys_stock_list）：基本信息 + industry_id / market_id / board_id 关联
sys_stock_industries、sys_stock_markets、sys_stock_boards 三个定义表；不再使用行业映射表。

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
            "name": "industry_id",
            "type": "int",
            "isRequired": False,
            "nullable": True,
            "description": "行业 id，关联 sys_stock_industries.id",
        },
        {
            "name": "market_id",
            "type": "int",
            "isRequired": False,
            "nullable": True,
            "description": "市场 id，关联 sys_stock_markets.id",
        },
        {
            "name": "board_id",
            "type": "int",
            "isRequired": False,
            "nullable": True,
            "description": "板块 id，关联 sys_stock_boards.id（如主板、科创板、创业板、北交所）",
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
