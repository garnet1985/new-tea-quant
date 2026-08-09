"""日频估值/基本面指标服务（``sys_stock_indicators``）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ... import BaseDataService
from core.infra.utils import Utils


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

        start = Utils.date.normalize(start_date, fmt=Utils.date.FMT_YYYYMMDD) if start_date else None
        end = Utils.date.normalize(end_date, fmt=Utils.date.FMT_YYYYMMDD) if end_date else None
        if start:
            conditions.append("date >= %s")
            params.append(start)
        if end:
            conditions.append("date <= %s")
            params.append(end)

        where_clause = " AND ".join(conditions)
        return model.load(where_clause, tuple(params), order_by="date ASC")

    def load_batch(
        self,
        stock_ids: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        批量加载多个股票的日频指标数据（优化：一次查询所有股票）。

        Args:
            stock_ids: 股票代码列表
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            Dict[stock_id, List[Dict]]: 每只股票的指标数据字典
        """
        if not stock_ids:
            return {}

        model = self._get_model()

        # 统一日期格式
        start = Utils.date.normalize(start_date, fmt=Utils.date.FMT_YYYYMMDD) if start_date else None
        end = Utils.date.normalize(end_date, fmt=Utils.date.FMT_YYYYMMDD) if end_date else None

        # 使用 IN 子句批量查询
        placeholders = ','.join(['%s'] * len(stock_ids))
        conditions = [f"id IN ({placeholders})"]
        params: list[Any] = list(stock_ids)

        if start:
            conditions.append("date >= %s")
            params.append(start)
        if end:
            conditions.append("date <= %s")
            params.append(end)

        where_clause = " AND ".join(conditions)
        all_rows = model.load(where_clause, tuple(params), order_by="id ASC, date ASC")

        # 按 stock_id 分组
        result: Dict[str, List[Dict[str, Any]]] = {sid: [] for sid in stock_ids}
        for row in all_rows:
            sid = row.get("id", "")
            if sid in result:
                result[sid].append(row)

        return result
