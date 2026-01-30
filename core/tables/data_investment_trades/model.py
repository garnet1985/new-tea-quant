"""
data_investment_trades 表 Model

投资交易。
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel
from core.tables.data_investment_trades.schema import schema as _schema


class DataInvestmentTradesModel(DbBaseModel):
    """投资交易表 Model（表名 data_investment_trades）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_schema(self) -> dict:
        return _schema

    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        return self.load("stock_id = %s", (stock_id,))

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.replace(records, unique_keys=["id"])
