"""
data_cpi 表结构定义（Python，变量名 schema）

消费者价格指数（原 price_indexes 拆分），月度，YYYYMM。
主键 date nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_cpi",
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
            "name": "cpi",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "CPI当月值",
        },
        {
            "name": "cpi_yoy",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "CPI同比",
        },
        {
            "name": "cpi_mom",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "CPI环比",
        },
    ],
    "indexes": [
        {"name": "idx_date", "fields": ["date"], "unique": True},
    ],
}
