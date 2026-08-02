"""
sys_trade_calendar 表 Model
"""
from typing import Any, Dict, List, Optional

from core.infra.db.contracts import DbBaseModel

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

    def load_max_cal_date_on_or_before(
        self,
        as_of_date: str,
        *,
        market: str = DEFAULT_MARKET,
        is_open_only: bool = False,
    ) -> str:
        """
        ``<= as_of_date`` 的 MAX(cal_date)。

        ``is_open_only=True``：仅 ``is_open=1``；否则含休市日在内所有已记载自然日。
        """
        d = str(as_of_date or "").strip()
        if not d:
            return ""
        if is_open_only:
            sql = """
                SELECT MAX(cal_date) AS max_date
                FROM sys_trade_calendar
                WHERE market = %s AND is_open = 1 AND cal_date <= %s
            """
        else:
            sql = """
                SELECT MAX(cal_date) AS max_date
                FROM sys_trade_calendar
                WHERE market = %s AND cal_date <= %s
            """
        rows = self.db.execute_sync_query(sql, (market, d)) or []
        if not rows:
            return ""
        return str(rows[0].get("max_date") or "").strip()

    def load_previous_open_date_before(
        self,
        before_date: str,
        *,
        market: str = DEFAULT_MARKET,
    ) -> str:
        """``< before_date`` 的最近一个开市日（``is_open=1``）。"""
        d = str(before_date or "").strip()
        if not d:
            return ""
        sql = """
            SELECT MAX(cal_date) AS max_date
            FROM sys_trade_calendar
            WHERE market = %s AND is_open = 1 AND cal_date < %s
        """
        rows = self.db.execute_sync_query(sql, (market, d)) or []
        if not rows:
            return ""
        return str(rows[0].get("max_date") or "").strip()

    def load_db_latest_completed_trading_date(
        self,
        *,
        market: str = DEFAULT_MARKET,
        as_of_date: Optional[str] = None,
    ) -> str:
        """库内已同步日历中，``<= as_of_date`` 最近一个开市日（``is_open=1``）。"""
        from core.infra.utils import Utils

        anchor = str(as_of_date or Utils.date.today()).strip()
        return self.load_max_cal_date_on_or_before(
            anchor, market=market, is_open_only=True
        )

    def load_db_latest_trading_date(
        self,
        *,
        market: str = DEFAULT_MARKET,
        as_of_date: Optional[str] = None,
        is_open_only: bool = False,
    ) -> str:
        """
        库内已同步日历中 ``<= as_of_date`` 最近一条记载。

        ``is_open_only=True`` 等同 ``load_db_latest_completed_trading_date``；默认含休市日。
        """
        if is_open_only:
            return self.load_db_latest_completed_trading_date(
                market=market, as_of_date=as_of_date
            )
        from core.infra.utils import Utils

        anchor = str(as_of_date or Utils.date.today()).strip()
        return self.load_max_cal_date_on_or_before(
            anchor, market=market, is_open_only=False
        )
