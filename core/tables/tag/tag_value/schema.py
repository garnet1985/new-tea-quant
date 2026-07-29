"""
sys_tag_value 表结构定义（Python，变量名 schema）

标签值（点事实）：某实体在某 as_of 的结果。
主键 (entity_id, tag_definition_id, as_of_date)。

SOT 边界：
- attach_to_data_key → sys_tag_scenario（不在本表重复）
- 计算推进 frontier → sys_tag_calc_progress（不是 as_of / calculated_at）
"""
schema = {
    "storage_domain": "tag",
    "update_key": "tag_tag_value",
    "name": "sys_tag_value",
    "primaryKey": ["entity_id", "tag_definition_id", "as_of_date"],
    "fields": [
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
            "description": "业务日期（结果点；不作增量水位）",
        },
        {
            "name": "start_date",
            "type": "date",
            "isRequired": False,
            "nullable": True,
            "description": "可选：该结果有效区间起点",
        },
        {
            "name": "end_date",
            "type": "date",
            "isRequired": False,
            "nullable": True,
            "description": "可选：该结果有效区间终点",
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
            "description": "落库墙钟时间（审计；不作业务水位）",
        },
    ],
    "indexes": [
        {"name": "idx_entity_date", "fields": ["entity_id", "as_of_date"]},
        {"name": "idx_tag_date", "fields": ["tag_definition_id", "as_of_date"]},
    ],
}
