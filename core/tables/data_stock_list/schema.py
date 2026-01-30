"""
data_stock_list 表结构定义（Python，变量名 schema）

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
            "name": "industry",
            "type": "text",
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
