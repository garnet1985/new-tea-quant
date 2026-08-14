"""
sys_stock_st_periods 表 Model
"""
from typing import Any, Dict, List, Optional, Sequence

from core.infra.db.contracts import DbBaseModel

from core.tables.stock.stock_st_periods.schema import schema as _schema


class StockStPeriodsModel(DbBaseModel):
    """股票 ST 时段表 Model"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        return self.load(
            "stock_id = %s",
            (stock_id,),
            order_by="start_date ASC",
        )

    def load_overlapping_window(
        self,
        stock_ids: Sequence[str],
        period_start: str,
        period_end: str,
    ) -> List[Dict[str, Any]]:
        ids = [str(s).strip() for s in stock_ids if str(s).strip()]
        if not ids:
            return []
        placeholders = ",".join(["%s"] * len(ids))
        sql = (
            f"stock_id IN ({placeholders}) "
            "AND start_date <= %s "
            "AND (end_date IS NULL OR end_date = '' OR end_date >= %s)"
        )
        params = tuple(ids) + (period_end, period_start)
        return self.load(sql, params, order_by="stock_id ASC, start_date ASC")

    def replace_for_stock(self, stock_id: str, periods: List[Dict[str, Any]]) -> int:
        self.delete("stock_id = %s", (stock_id,))
        if not periods:
            return 0
        return self.upsert_many(
            periods,
            unique_keys=["stock_id", "st_level", "start_date"],
        )
