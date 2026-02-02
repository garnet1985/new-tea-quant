"""
系统缓存（sys_cache）：key-value，value 存文本。

与 sys_meta_info 区分：本表 value 为 text；meta_info 为 json。二者均有 created_at、last_updated。
主键 key nullable=false；其余 nullable=true。
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
            "name": "text",
            "type": "text",
            "isRequired": True,
            "nullable": True,
            "description": "缓存值，文本格式",
        },
        {
            "name": "json",
            "type": "json",
            "isRequired": True,
            "nullable": True,
            "description": "缓存值，JSON 格式",
        },
        {
            "name": "created_at",
            "type": "datetime",
            "isRequired": True,
            "nullable": True,
            "description": "创建时间",
        },
        {
            "name": "last_updated",
            "type": "datetime",
            "isRequired": True,
            "nullable": True,
            "description": "最后更新时间",
        },
    ],
}
