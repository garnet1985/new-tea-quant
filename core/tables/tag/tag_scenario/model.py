"""
sys_tag_scenario 表 Model

业务场景。
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel
from core.tables.tag.tag_scenario.schema import schema as _schema


class SysTagScenarioModel(DbBaseModel):
    """业务场景表 Model（表名 sys_tag_scenario）

    设计约定：
    - Model 层只提供“底层表访问 + 通用同步接口”，不承载具体业务规则
    - 例如按 name 的唯一性校验、场景生命周期等逻辑，由 `TagDataService` 统一封装
    """

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """按唯一 name 加载单条 scenario"""
        return self.load_one("name = %s", (name,))

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        """批量 upsert，按主键 id 去重（由同步脚本使用）"""
        return self.upsert_many(records, unique_keys=["id"])
