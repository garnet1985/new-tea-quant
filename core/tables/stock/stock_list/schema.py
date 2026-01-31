"""
股票列表（sys_stock_list）：不含 industry 列，行业通过 sys_industries + sys_stock_industries 关联。

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
            "name": "type",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": True,
        },
        {
            "name": "exchange_center",
            "type": "varchar",
            "length": 16,
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
