"""
地域定义表 Model（表名 sys_areas）
"""
from typing import List, Dict, Any, Optional
from core.infra.db.contracts import DbBaseModel

from core.tables.stock.areas.schema import schema as _schema


class AreasModel(DbBaseModel):
    """地域定义表 Model（表名 sys_areas）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_id(self, area_id: int) -> Optional[Dict[str, Any]]:
        return self.load_one("id = %s", (area_id,))

    def load_by_value(self, value: str) -> Optional[Dict[str, Any]]:
        return self.load_one("value = %s", (value,))

    def load_alive(self) -> List[Dict[str, Any]]:
        return self.load("is_alive = 1", order_by="id ASC")
