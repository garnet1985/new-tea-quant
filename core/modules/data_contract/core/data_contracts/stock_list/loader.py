"""StockList Loader。"""
from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence

from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader
from core.modules.data_manager import DataManager


class StockListLoader(BaseDataContractLoader):
    """Loader for stock list; delegates to ListService.load / load_single."""

    def load(self, params: Mapping[str, Any]) -> Any:
        svc = DataManager().stock.list
        order_by = str(params.get("order_by", "id"))

        stock_id = params.get("stock_id")
        if stock_id is not None:
            row = svc.load_single(str(stock_id))
            return [row] if row else []

        return svc.load(
            period_start=params.get("period_start"),
            period_end=params.get("period_end"),
            as_of_date=params.get("as_of_date") or params.get("trade_date"),
            list_status=params.get("list_status"),
            industry=params.get("industry"),
            board=params.get("board"),
            market=params.get("market"),
            area=params.get("area"),
            order_by=order_by,
        )

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """
        批量加载股票列表数据。

        注意：stock.list 是 GLOBAL scope 数据，
        所有 entity 共享同一份数据，因此直接调用 load() 并返回。
        """
        # GLOBAL scope：所有 entity 返回相同的数据
        data = self.load(params)
        return {str(eid).strip(): data for eid in entity_ids if str(eid).strip()}