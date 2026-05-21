from __future__ import annotations

from typing import Any, List, Mapping, Optional

from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_manager import DataManager


class StockListLoader(BaseLoader):
    """Loader for stock list; delegates to ListService.load / load_single."""

    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
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
