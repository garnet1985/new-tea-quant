"""
sys_data_index_klines 表 Model

股指 K 线。
"""
from typing import List, Dict, Any
from core.infra.db.contracts import DbBaseModel
from core.tables.index.stock_index_klines.schema import schema as _schema


class DataStockIndexKlinesModel(DbBaseModel):
    """股指 K 线表 Model（表名 sys_data_index_klines）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.upsert_many(records, unique_keys=["id", "term", "date"])
