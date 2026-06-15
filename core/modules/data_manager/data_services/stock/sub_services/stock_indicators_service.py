"""日频估值/基本面指标服务（``sys_stock_indicators``）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.utils.date.date_utils import DateUtils

from ... import BaseDataService


class StockIndicatorsService(BaseDataService):
    """股票日频指标（PE/PB/市值等），与 K 线表分离。"""

    def __init__(self, data_manager: Any) -> None:
        super().__init__(data_manager)
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = self.data_manager.get_table("sys_stock_indicators")
        return self._model

    def load_range(
        self,
        stock_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """按日期区间加载指标行（升序）。"""
        model = self._get_model()
        conditions = ["id = %s"]
        params: list[Any] = [stock_id]

        start = DateUtils.normalize(start_date, fmt=DateUtils.FMT_YYYYMMDD) if start_date else None
        end = DateUtils.normalize(end_date, fmt=DateUtils.FMT_YYYYMMDD) if end_date else None
        if start:
            conditions.append("date >= %s")
            params.append(start)
        if end:
            conditions.append("date <= %s")
            params.append(end)

        where_clause = " AND ".join(conditions)
        return model.load(where_clause, tuple(params), order_by="date ASC")
