"""
sys_tag_calc_progress 表结构定义（Python，变量名 schema）

Tag 增量计算水位（业务推进 frontier），与 sys_tag_value 同属 tag 域。

语义（SOT）：
- 记录「某 scenario 下某 entity 已成功算到的业务日」last_calculated_end（YYYYMMDD）
- 不是 max(as_of) / calculated_at：变化日写入的 tag 仍按扫过的交易日推进
- 仅覆盖当前 entity list 中出现过的实体：
  - 新实体无行 → 从 settings 起点算
  - 不在 list 中的残留行忽略、不更新
- refresh / recompute 清值时按 scenario_id 整表删除
- entity_based / slice_based 共用本表；slice 成功后可将本跑实体批量推进到同一 end

主键 (scenario_id, entity_id)；无自增 id。
"""
schema = {
    "storage_domain": "tag",
    "update_key": "tag_tag_calc_progress",
    "name": "sys_tag_calc_progress",
    "primaryKey": ["scenario_id", "entity_id"],
    "fields": [
        {
            "name": "scenario_id",
            "type": "bigint",
            "isRequired": True,
            "nullable": False,
            "description": "外键 → sys_tag_scenario.id",
        },
        {
            "name": "entity_id",
            "type": "varchar",
            "length": 64,
            "isRequired": True,
            "nullable": False,
            "description": "实体 ID（与 sys_tag_value.entity_id 同语义）",
        },
        {
            "name": "last_calculated_end",
            "type": "date",
            "isRequired": True,
            "nullable": False,
            "description": "已成功算到的业务日（含当日）；续跑从次一交易日/次一日历策略日起",
        },
        {
            "name": "updated_at",
            "type": "datetime",
            "isRequired": True,
            "nullable": True,
            "default": "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
            "description": "水位写入墙钟时间（不作业务水位）",
        },
    ],
    "indexes": [
        {
            "name": "idx_scenario_id",
            "fields": ["scenario_id"],
            "description": "按 scenario 批量加载 / refresh 时整场景清除",
        },
        {
            "name": "idx_scenario_end",
            "fields": ["scenario_id", "last_calculated_end"],
            "description": "可选：按场景查落后实体 / 汇总进度",
        },
    ],
}
