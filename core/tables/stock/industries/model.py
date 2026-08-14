"""
行业定义表 Model（表名 sys_industries）
"""
from typing import List, Dict, Any, Optional
from core.infra.db.contracts import DbBaseModel

from core.tables.stock.industries.schema import schema as _schema


class IndustriesModel(DbBaseModel):
    """行业定义表 Model（表名 sys_industries）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_id(self, industry_id: int) -> Optional[Dict[str, Any]]:
        return self.load_one("id = %s", (industry_id,))

    def load_by_value(self, value: str) -> Optional[Dict[str, Any]]:
        return self.load_one("value = %s", (value,))

    def load_alive(self) -> List[Dict[str, Any]]:
        return self.load("is_alive = 1", order_by="id ASC")
