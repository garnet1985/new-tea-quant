"""
data_corporate_finance 表 Model

企业财务数据。
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel
from core.tables.stock.corporate_finance.schema import schema as _schema


class DataCorporateFinanceModel(DbBaseModel):
    """企业财务表 Model（表名 data_corporate_finance）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        return self.load("id = %s", (stock_id,), order_by="quarter ASC")

    def load_by_quarter(self, stock_id: str, quarter: str) -> Optional[Dict[str, Any]]:
        return self.load_one("id = %s AND quarter = %s", (stock_id, quarter))

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.upsert_many(records, unique_keys=["id", "quarter"])
