"""
data_investment_operations 表 Model

投资操作记录。
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel
from core.tables.data_investment_operations.schema import schema as _schema


class DataInvestmentOperationsModel(DbBaseModel):
    """投资操作表 Model（表名 data_investment_operations）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_schema(self) -> dict:
        return _schema

    def load_by_trade(self, trade_id: int) -> List[Dict[str, Any]]:
        return self.load("trade_id = %s", (trade_id,), order_by="date ASC")

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.replace(records, unique_keys=["id"])
