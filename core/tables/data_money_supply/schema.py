"""
data_money_supply 表结构定义（Python，变量名 schema）

货币供应量（原 price_indexes 拆分），月度，YYYYMM。
主键 date nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_money_supply",
    "primaryKey": "date",
    "fields": [
        {
            "name": "date",
            "type": "varchar",
            "length": 6,
            "isRequired": True,
            "nullable": False,
            "description": "月份 YYYYMM",
        },
        {
            "name": "m0",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "M0",
        },
        {
            "name": "m0_yoy",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "M0同比",
        },
        {
            "name": "m0_mom",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "M0环比",
        },
        {
            "name": "m1",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "M1",
        },
        {
            "name": "m1_yoy",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "M1同比",
        },
        {
            "name": "m1_mom",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "M1环比",
        },
        {
            "name": "m2",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "M2",
        },
        {
            "name": "m2_yoy",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "M2同比",
        },
        {
            "name": "m2_mom",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "M2环比",
        },
    ],
    "indexes": [
        {"name": "idx_date", "fields": ["date"], "unique": True},
    ],
}
