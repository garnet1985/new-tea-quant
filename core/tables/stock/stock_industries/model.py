"""
data_stock_industries 表 Model

股票–行业映射表。
"""
from typing import List, Dict, Any
from core.infra.db import DbBaseModel

from core.tables.stock.stock_industries.schema import schema as _schema


class DataStockIndustriesModel(DbBaseModel):
    """股票行业映射表 Model（表名 data_stock_industries）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_schema(self) -> dict:
        """从本表 schema.py 加载"""
        return _schema

    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        """查询某股票所属行业"""
        return self.load("stock_id = %s", (stock_id,))

    def load_by_industry(self, industry_id: int) -> List[Dict[str, Any]]:
        """查询某行业下的股票"""
        return self.load("industry_id = %s", (industry_id,))

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        """批量保存（按 stock_id + industry_id 去重）"""
        return self.replace(records, unique_keys=["stock_id", "industry_id"])
