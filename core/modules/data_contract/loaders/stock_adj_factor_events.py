from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

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
        sid = _stock_id(params, context)
        start = params.get("start")
        end = params.get("end")
        return dm.stock.kline.load_adj_factor_events(
            stock_id=sid,
            start_date=str(start) if start else None,
            end_date=str(end) if end else None,
        )

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
        context: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        """
        批量加载多个股票的复权因子事件序列（使用 SQL WHERE IN 优化）。

        Args:
            entity_ids: 股票代码列表
            params: 加载参数（包含 start/end）
            context: 未使用（批量路径由 entity_ids 驱动）

        Returns:
            Dict[stock_id, List[Dict]]: 每只股票的复权因子事件数据
        """
        del context  # 批量路径由 entity_ids 驱动，不依赖单股 context

        ids = [str(x).strip() for x in entity_ids if str(x).strip()]
        if not ids:
            return {}

        dm = DataManager()
        start = str(params.get("start")) if params.get("start") is not None else None
        end = str(params.get("end")) if params.get("end") is not None else None

        # 调用 service 层的批量 API
        return dm.stock.kline.load_adj_factor_events_batch(
            ids,
            start_date=start,
            end_date=end,
        )
