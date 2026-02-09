"""
data_shibor 表结构定义（Python，变量名 schema）

上海银行间同业拆放利率。主键 date nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_shibor",
    "primaryKey": ["date"],
    "fields": [
        {
            "name": "date",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "日期 YYYYMMDD",
        },
        {
            "name": "one_night",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "隔夜",
        },
        {
            "name": "one_week",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "一周",
        },
        {
            "name": "one_month",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "一个月",
        },
        {
            "name": "three_month",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "三个月",
        },
        {
            "name": "one_year",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "一年",
        },
    ],
}
