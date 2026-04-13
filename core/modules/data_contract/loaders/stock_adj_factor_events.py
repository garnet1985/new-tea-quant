from __future__ import annotations

from typing import Any, Mapping, Optional

from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_manager import DataManager


def _stock_id(params: Mapping[str, Any], context: Optional[Mapping[str, Any]]) -> str:
    c = context or {}
    sid = params.get("stock_id") or params.get("id") or c.get("stock_id") or c.get("id") or c.get("entity_id")
    if not sid:
        raise ValueError("加载 stock.adj_factor.eventlog 失败：缺少 stock_id（请在 context 中提供）")
    return str(sid)


class StockAdjFactorEventsLoader(BaseLoader):
    """按股票加载 sys_adj_factor_events（事件序列）。"""

    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        dm = DataManager()
        model = dm.get_table("sys_adj_factor_events")
        if not model:
            raise RuntimeError("加载 stock.adj_factor.eventlog 失败：未注册 sys_adj_factor_events 表")
        sid = _stock_id(params, context)
        return model.load("id = %s", (sid,), order_by="event_date ASC") or []
