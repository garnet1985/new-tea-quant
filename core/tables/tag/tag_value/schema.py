"""
sys_tag_value 表结构定义（Python，变量名 schema）

标签值。主键 entity_id/tag_definition_id/as_of_date nullable=false；其余 nullable=true。
"""
schema = {
    "name": "sys_tag_value",
    "primaryKey": ["entity_id", "tag_definition_id", "as_of_date"],
    "fields": [
        {
            "name": "entity_type",
            "type": "varchar",
            "length": 32,
            "isRequired": True,
            "nullable": True,
            "default": "stock",
            "description": "实体类型，默认 stock",
        },
        {
            "name": "entity_id",
            "type": "varchar",
            "length": 64,
            "isRequired": True,
            "nullable": False,
            "description": "实体ID",
        },
        {
            "name": "tag_definition_id",
            "type": "bigint",
            "isRequired": True,
            "nullable": False,
            "description": "标签定义ID",
        },
        {
            "name": "as_of_date",
            "type": "date",
            "isRequired": True,
            "nullable": False,
            "description": "业务日期",
        },
        {
            "name": "start_date",
            "type": "date",
            "isRequired": False,
            "nullable": True,
            "description": "tag 起始日期",
        },
        {
            "name": "end_date",
            "type": "date",
            "isRequired": False,
            "nullable": True,
            "description": "tag 结束日期",
        },
        {
            "name": "json_value",
            "type": "json",
            "isRequired": True,
            "nullable": True,
            "description": "标签值 JSON",
        },
        {
            "name": "calculated_at",
            "type": "datetime",
            "isRequired": True,
            "nullable": True,
            "default": "CURRENT_TIMESTAMP",
            "description": "计算时间",
        },
    ],
    "indexes": [
        {"name": "idx_entity_date", "fields": ["entity_id", "as_of_date"]},
        {"name": "idx_tag_date", "fields": ["tag_definition_id", "as_of_date"]},
    ],
}
