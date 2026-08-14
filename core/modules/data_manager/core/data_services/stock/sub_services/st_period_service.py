"""
股票 ST / *ST 风险警示时段服务（StPeriodService）

数据来自 sys_stock_st_periods（namechange 同步）。
运行时建议：回测 run 内调用 load_overlapping 一次，按日判断走内存。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from core.tables.stock.stock_st_periods.st_period_rules import (
    ALL_ST_LEVELS,
    ST_LEVEL_STAR_ST,
    ST_LEVEL_ST,
    is_active_on,
    normalize_yyyymmdd,
)

from ... import BaseDataService


class StPeriodService(BaseDataService):
    """ST 风险警示时段查询"""

    def __init__(self, data_manager: Any):
        super().__init__(data_manager)
        self._model = data_manager.get_table("sys_stock_st_periods")

    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        """某股全部 ST 时段（通常很少）。"""
        return self._model.load_by_stock(str(stock_id).strip())

    def load_overlapping(
        self,
        stock_ids: Sequence[str],
        *,
        period_start: str,
        period_end: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        与 [period_start, period_end] 有交集的时段，按 stock_id 分组。
        每个 run 调用一次即可，后续 is_on 走内存。
        """
        rows = self._model.load_overlapping_window(
            stock_ids,
            normalize_yyyymmdd(period_start),
            normalize_yyyymmdd(period_end),
        )
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            sid = str(row.get("stock_id") or "").strip()
            if not sid:
                continue
            grouped.setdefault(sid, []).append(row)
        return grouped

    def is_on(
        self,
        stock_id: str,
        trade_date: str,
        *,
        levels: Optional[Sequence[str]] = None,
        periods: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> bool:
        """
        某日是否处于风险警示（默认含 ST 与 *ST 等等级）。

        periods 非空时不再访问 DB（供 run 级缓存）。
        """
        level_tuple: Optional[Tuple[str, ...]] = None
        if levels is not None:
            level_tuple = tuple(str(x) for x in levels if x)
        rows = list(periods) if periods is not None else self.load_by_stock(stock_id)
        for row in rows:
            if is_active_on(row, trade_date, levels=level_tuple):
                return True
        return False

    def is_star_st_on(
        self,
        stock_id: str,
        trade_date: str,
        *,
        periods: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> bool:
        """某日是否为 *ST（STAR_ST）。"""
        return self.is_on(
            stock_id,
            trade_date,
            levels=(ST_LEVEL_STAR_ST,),
            periods=periods,
        )

    def is_st_on(
        self,
        stock_id: str,
        trade_date: str,
        *,
        include_star_st: bool = True,
        periods: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> bool:
        """某日是否为 ST；默认包含 *ST。"""
        if include_star_st:
            return self.is_on(
                stock_id,
                trade_date,
                levels=ALL_ST_LEVELS,
                periods=periods,
            )
        return self.is_on(
            stock_id,
            trade_date,
            levels=(ST_LEVEL_ST,),
            periods=periods,
        )

    @staticmethod
    def level_at(
        trade_date: str,
        periods: Sequence[Dict[str, Any]],
        *,
        levels: Optional[Sequence[str]] = None,
    ) -> Optional[str]:
        """返回当日生效的最高优先级 level（*ST > ST > …），无则 None。"""
        d = normalize_yyyymmdd(trade_date)
        if not d:
            return None
        priority = (
            ST_LEVEL_STAR_ST,
            "S_STAR_ST",
            "SST",
            ST_LEVEL_ST,
        )
        allowed = set(levels) if levels is not None else None
        active = [
            str(p.get("st_level") or "")
            for p in periods
            if is_active_on(p, d, levels=tuple(levels) if levels else None)
        ]
        if not active:
            return None
        for pref in priority:
            if pref in active and (allowed is None or pref in allowed):
                return pref
        return active[0]
