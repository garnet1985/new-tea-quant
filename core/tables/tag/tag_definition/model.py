"""
sys_tag_definition 表 Model

标签定义。
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel
from core.tables.tag.tag_definition.schema import schema as _schema


class SysTagDefinitionModel(DbBaseModel):
    """标签定义表 Model（表名 sys_tag_definition）

    设计约定：
    - Model 层只提供“底层表访问 + 通用同步接口”，不包含领域逻辑
    - 具体查询 / upsert 规则（如按 scenario_id、name 的组合约束）统一放在
      DataManager 的 `TagDataService` 中实现
    """

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_scenario(self, scenario_id: int) -> List[Dict[str, Any]]:
        """兼容旧接口：按 scenario_id 加载全部定义"""
        return self.load("scenario_id = %s", (scenario_id,))

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        """批量 upsert，按主键 id 去重（由同步脚本使用）"""
        return self.upsert_many(records, unique_keys=["id"])
