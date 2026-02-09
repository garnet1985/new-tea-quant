"""
data_stock_index_indicator_weight 表 Model

股指成分股权重。
"""
from typing import List, Dict, Any
from core.infra.db import DbBaseModel
from core.tables.index.stock_index_weight.schema import schema as _schema


class DataStockIndexWeightModel(DbBaseModel):
    """股指成分股权重表 Model（表名 data_stock_index_weight）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.upsert_many(records, unique_keys=["id", "date", "stock_id"])
