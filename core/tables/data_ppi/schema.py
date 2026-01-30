"""
data_ppi 表结构定义（Python，变量名 schema）

生产者价格指数（原 price_indexes 拆分），月度，YYYYMM。
主键 date nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_ppi",
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
            "name": "ppi",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "PPI当月值",
        },
        {
            "name": "ppi_yoy",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "PPI同比",
        },
        {
            "name": "ppi_mom",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "PPI环比",
        },
    ],
    "indexes": [
        {"name": "idx_date", "fields": ["date"], "unique": True},
    ],
}
