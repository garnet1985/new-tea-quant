from __future__ import annotations

from typing import Any, Mapping, Optional

from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_manager import DataManager
from core.utils.date.date_utils import DateUtils


def _stock_id(params: Mapping[str, Any], context: Optional[Mapping[str, Any]]) -> str:
    c = context or {}
    sid = params.get("stock_id") or params.get("id") or c.get("stock_id") or c.get("id") or c.get("entity_id")
    if not sid:
        raise ValueError("加载 stock.moneyflow.daily 失败：缺少 stock_id（请在 context 中提供）")
    return str(sid)


class StockMoneyflowDailyLoader(BaseLoader):
    """按股票加载 ``sys_stock_moneyflow`` 日频序列。"""

    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        dm = DataManager()
        sid = _stock_id(params, context)
        start = DateUtils.normalize_str(params.get("start")) if params.get("start") is not None else None
        end = DateUtils.normalize_str(params.get("end")) if params.get("end") is not None else None
        return dm.stock.moneyflow.load_range(sid, start_date=start, end_date=end)
