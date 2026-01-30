"""
data_adj_factor_event 表 Model

复权因子事件，只存储除权除息日的因子变化。
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.infra.db import DbBaseModel
from core.tables.data_adj_factor_event.schema import schema as _schema


class DataAdjFactorEventModel(DbBaseModel):
    """复权因子事件表 Model（表名 data_adj_factor_event）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_schema(self) -> dict:
        return _schema

    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        return self.load("id = %s", (stock_id,), order_by="event_date ASC")

    def load_by_date_range(
        self, stock_id: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        return self.load(
            "id = %s AND event_date BETWEEN %s AND %s",
            (stock_id, start_date.replace("-", ""), end_date.replace("-", "")),
            order_by="event_date ASC",
        )

    def load_factor_by_date(self, stock_id: str, date: str) -> Optional[Dict[str, Any]]:
        date_ymd = date.replace("-", "") if "-" in date else date
        return self.load_one(
            "id = %s AND event_date <= %s", (stock_id, date_ymd), order_by="event_date DESC"
        )

    def load_latest_factor(self, stock_id: str) -> Optional[Dict[str, Any]]:
        return self.load_one("id = %s", (stock_id,), order_by="event_date DESC")

    def save_events(self, events: List[Dict[str, Any]]) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for e in events:
            e.setdefault("last_update", now)
            if "event_date" in e:
                e["event_date"] = str(e["event_date"]).replace("-", "")[:8]
        return self.replace(events, unique_keys=["id", "event_date"])
