"""
stock_industries 表 Model

行业维度表，与 stock_list 配合使用。
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel

from core.tables.stock.stock_industries.schema import schema as _schema


class DataIndustriesModel(DbBaseModel):
    """行业维度表 Model（表名 sys_stock_industries）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_schema(self) -> dict:
        """从本表 schema.py 加载"""
        return _schema

    def load_by_id(self, industry_id: int) -> Optional[Dict[str, Any]]:
        """按 id 查询"""
        return self.load_one("id = %s", (industry_id,))

    def load_by_value(self, value: str) -> Optional[Dict[str, Any]]:
        """按行业名查询"""
        return self.load_one("value = %s", (value,))

    def load_alive(self) -> List[Dict[str, Any]]:
        """查询所有有效行业"""
        return self.load("is_alive = 1", order_by="id ASC")

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        """批量保存（按 id 去重，若 id 自增则需先查再写或由 DB 生成）"""
        return self.replace(records, unique_keys=["id"])
