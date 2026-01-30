"""
sys_tag_scenario 表结构定义（Python，变量名 schema）

业务场景。主键 id nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_tag_scenario",
    "primaryKey": "id",
    "fields": [
        {
            "name": "id",
            "type": "bigint",
            "isRequired": True,
            "nullable": False,
            "autoIncrement": True,
            "description": "自增主键",
        },
        {
            "name": "name",
            "type": "varchar",
            "length": 64,
            "isRequired": True,
            "nullable": True,
            "description": "业务场景唯一代码",
        },
        {
            "name": "display_name",
            "type": "varchar",
            "length": 128,
            "isRequired": False,
            "nullable": True,
            "description": "业务场景显示名称",
        },
        {
            "name": "description",
            "type": "text",
            "isRequired": False,
            "nullable": True,
            "description": "业务场景描述",
        },
        {
            "name": "created_at",
            "type": "datetime",
            "isRequired": True,
            "nullable": True,
            "default": "CURRENT_TIMESTAMP",
            "description": "创建时间",
        },
        {
            "name": "updated_at",
            "type": "datetime",
            "isRequired": True,
            "nullable": True,
            "default": "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
            "description": "更新时间",
        },
    ],
    "indexes": [
        {"name": "uk_name", "fields": ["name"], "unique": True},
    ],
}
