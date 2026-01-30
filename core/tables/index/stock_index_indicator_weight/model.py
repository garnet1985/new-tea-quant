"""
data_stock_index_indicator_weight 表 Model

股指成分股权重。
"""
from typing import List, Dict, Any
from core.infra.db import DbBaseModel
from core.tables.data_stock_index_indicator_weight.schema import schema as _schema


class DataStockIndexIndicatorWeightModel(DbBaseModel):
    """股指成分股权重表 Model（表名 data_stock_index_indicator_weight）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_schema(self) -> dict:
        return _schema

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.replace(records, unique_keys=["id", "date", "stock_id"])
