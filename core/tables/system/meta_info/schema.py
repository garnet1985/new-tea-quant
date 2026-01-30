"""
sys_meta_info 表结构定义（Python，变量名 schema）

系统元信息（原 meta_info）。主键 id nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_meta_info",
    "primaryKey": "id",
    "fields": [
        {
            "name": "id",
            "type": "int",
            "isRequired": True,
            "nullable": False,
            "autoIncrement": True,
        },
        {
            "name": "info",
            "type": "text",
            "isRequired": True,
            "nullable": True,
        },
    ],
}
