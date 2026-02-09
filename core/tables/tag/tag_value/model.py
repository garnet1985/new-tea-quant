"""
sys_tag_value 表 Model

标签值。
"""
from typing import List, Dict, Any
from core.infra.db import DbBaseModel
from core.tables.tag.tag_value.schema import schema as _schema


class SysTagValueModel(DbBaseModel):
    """标签值表 Model（表名 sys_tag_value）

    设计约定：
    - Model 只负责底层表访问和通用“批量同步”接口
    - 唯一键的含义、增量更新策略等业务规则留在 `TagDataService` 实现
    """

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        """批量 upsert，按 (entity_id, tag_definition_id, as_of_date) 唯一键"""
        return self.upsert_many(
            records,
            unique_keys=["entity_id", "tag_definition_id", "as_of_date"],
        )

    # ------------------------------------------------------------------ #
    # 供 TagDataService 使用的领域接口
    # ------------------------------------------------------------------ #
    def save_tag_value(self, tag_value_data: Dict[str, Any]) -> int:
        """保存 / 更新单个 tag value"""
        return self.save_records([tag_value_data])

    def batch_save_tag_values(self, tag_values: List[Dict[str, Any]]) -> int:
        """批量保存 / 更新 tag values"""
        if not tag_values:
            return 0
        return self.save_records(tag_values)
