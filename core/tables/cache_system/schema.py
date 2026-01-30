"""
cache_system 表结构定义（Python，变量名 schema）

系统缓存（原 system_cache）。主键 key nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_cache",
    "primaryKey": "key",
    "fields": [
        {
            "name": "key",
            "type": "varchar",
            "length": 100,
            "isRequired": True,
            "nullable": False,
        },
        {
            "name": "value",
            "type": "varchar",
            "length": 255,
            "isRequired": True,
            "nullable": True,
        },
        {
            "name": "updated_at",
            "type": "datetime",
            "isRequired": True,
            "nullable": True,
        },
    ],
}
