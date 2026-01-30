"""
data_gdp 表结构定义（Python，变量名 schema）

国内生产总值。主键 quarter nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_gdp",
    "primaryKey": ["quarter"],
    "fields": [
        {
            "name": "quarter",
            "type": "varchar",
            "length": 16,
            "isRequired": True,
            "nullable": False,
            "description": "季度 YYYYQ[1-4]",
        },
        {
            "name": "gdp",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "GDP",
        },
        {
            "name": "gdp_yoy",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "GDP同比",
        },
        {
            "name": "primary_industry",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "GDP第一产业",
        },
        {
            "name": "primary_industry_yoy",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "GDP第一产业同比",
        },
        {
            "name": "secondary_industry",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "GDP第二产业",
        },
        {
            "name": "secondary_industry_yoy",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "GDP第二产业同比",
        },
        {
            "name": "tertiary_industry",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "GDP第三产业",
        },
        {
            "name": "tertiary_industry_yoy",
            "type": "float",
            "isRequired": True,
            "nullable": True,
            "description": "GDP第三产业同比",
        },
    ],
}
