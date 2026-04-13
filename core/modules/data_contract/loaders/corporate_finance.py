from __future__ import annotations

from typing import Any, Mapping, Optional

from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_manager import DataManager


def _stock_id(params: Mapping[str, Any], context: Optional[Mapping[str, Any]]) -> str:
    c = context or {}
    sid = params.get("stock_id") or params.get("id") or c.get("stock_id") or c.get("id") or c.get("entity_id")
    if not sid:
        raise ValueError("加载 corporate finance 失败：缺少 stock_id（请在 context 中提供）")
    return str(sid)


class CorporateFinanceLoader(BaseLoader):
    """按股票加载 sys_corporate_finance（季度序列）。"""

    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        dm = DataManager()
        sid = _stock_id(params, context)
        # 使用极宽季度范围等价于“全量季度序列”
        return dm.stock.corporate_finance.load_trend(
            sid,
            start_quarter="0000Q1",
            end_quarter="9999Q4",
        )
