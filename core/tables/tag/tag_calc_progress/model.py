"""
sys_tag_calc_progress 表 Model

Tag 增量计算水位（frontier）。
"""
from typing import List, Dict, Any
from core.infra.db.contracts import DbBaseModel
from core.tables.tag.tag_calc_progress.schema import schema as _schema


class SysTagCalcProgressModel(DbBaseModel):
    """计算进度表 Model（表名 sys_tag_calc_progress）

    设计约定：
    - Model 只负责底层表访问与通用 upsert
    - 水位语义（max 推进、按 scenario 清除）由 TagDataService 封装
    """

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        """批量 upsert，按 (scenario_id, entity_id) 唯一键。"""
        return self.upsert_many(
            records,
            unique_keys=["scenario_id", "entity_id"],
        )
