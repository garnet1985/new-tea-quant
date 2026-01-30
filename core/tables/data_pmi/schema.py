"""
data_pmi 表结构定义（Python，变量名 schema）

采购经理人指数（原 price_indexes 拆分），月度，YYYYMM。
主键 date nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_pmi",
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
            "name": "pmi",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "PMI综合指数",
        },
        {
            "name": "pmi_l_scale",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "大型企业PMI",
        },
        {
            "name": "pmi_m_scale",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "中型企业PMI",
        },
        {
            "name": "pmi_s_scale",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "小型企业PMI",
        },
    ],
    "indexes": [
        {"name": "idx_date", "fields": ["date"], "unique": True},
    ],
}
