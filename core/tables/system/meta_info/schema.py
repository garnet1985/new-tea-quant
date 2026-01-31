"""
系统元信息（sys_meta_info）：结构化元数据，value 存 JSON。

与 sys_cache 区分：本表 value 为 json；cache 的 value 为 text。二者均有 created_at、last_updated。
主键 id nullable=false；其余 nullable=true。
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
            "name": "value",
            "type": "json",
            "isRequired": True,
            "nullable": True,
            "description": "元信息内容，JSON 格式",
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
