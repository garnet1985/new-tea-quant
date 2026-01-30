"""
data_stock_index_indicator_weight 表结构定义（Python，变量名 schema）

股指成分股权重。主键 id/date/stock_id nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_stock_index_indicator_weight",
    "primaryKey": ["id", "date", "stock_id"],
    "fields": [
        {
            "name": "id",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "股指代码",
        },
        {
            "name": "date",
            "type": "varchar",
            "length": 8,
            "isRequired": True,
            "nullable": False,
            "description": "日期 YYYYMMDD",
        },
        {
            "name": "stock_id",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "成分股代码",
        },
        {
            "name": "weight",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "权重",
        },
    ],
}
