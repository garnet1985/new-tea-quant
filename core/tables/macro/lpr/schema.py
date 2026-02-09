"""
data_lpr 表结构定义（Python，变量名 schema）

贷款基础利率，一年期和五年期。主键 date nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_lpr",
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
            "name": "lpr_1_y",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "一年期 LPR",
        },
        {
            "name": "lpr_5_y",
            "type": "float",
            "isRequired": False,
            "nullable": True,
            "description": "五年期 LPR",
        },
    ],
}
