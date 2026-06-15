from __future__ import annotations

from typing import Any, Mapping, Optional

from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_manager import DataManager


def _stock_id(params: Mapping[str, Any], context: Optional[Mapping[str, Any]]) -> str:
    c = context or {}
    sid = (
        params.get("stock_id")
        or params.get("id")
        or c.get("stock_id")
        or c.get("id")
        or c.get("entity_id")
    )
    if not sid:
        raise ValueError("加载 stock.indicators.daily 失败：缺少 stock_id（请在 context 中提供）")
    return str(sid)


class StockIndicatorsDailyLoader(BaseLoader):
    """按股票加载 sys_stock_indicators（日频 PE/PB/市值等）。"""

    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        dm = DataManager()
        sid = _stock_id(params, context)
        model = dm.get_table("sys_stock_indicators")
        start = params.get("start")
        end = params.get("end")
        if start is not None and end is not None:
            return model.load_by_date_range(sid, str(start), str(end))
        return model.load_by_stock(sid)
