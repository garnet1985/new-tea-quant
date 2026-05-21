"""
sys_trade_calendar 表 Model
"""
from typing import Any, Dict, List, Optional

from core.infra.db import DbBaseModel

from core.tables.calendar.trade_calendar.schema import schema as _schema

DEFAULT_MARKET = "SSE"


class TradeCalendarModel(DbBaseModel):
    """A 股交易日历 Model"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_date(
        self,
        cal_date: str,
        *,
        market: str = DEFAULT_MARKET,
    ) -> Optional[Dict[str, Any]]:
        return self.load_one(
            "market = %s AND cal_date = %s",
            (market, cal_date),
        )

    def load_range(
        self,
        start_date: str,
        end_date: str,
        *,
        market: str = DEFAULT_MARKET,
        is_open: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        sql = "market = %s AND cal_date >= %s AND cal_date <= %s"
        params: List[Any] = [market, start_date, end_date]
        if is_open is not None:
            sql += " AND is_open = %s"
            params.append(is_open)
        return self.load(sql, tuple(params), order_by="cal_date ASC")
