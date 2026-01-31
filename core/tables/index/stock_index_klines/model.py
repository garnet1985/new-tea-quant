"""
data_stock_index_indicator 表 Model

股指指标。
"""
from typing import List, Dict, Any
from core.infra.db import DbBaseModel
from core.tables.index.stock_index_klines.schema import schema as _schema


class DataStockIndexKlinesModel(DbBaseModel):
    """股指K线表 Model（表名 data_stock_index_klines）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.replace(records, unique_keys=["id", "term", "date"])
