from __future__ import annotations

from typing import Any, Mapping, Optional

from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_manager import DataManager


class StockListLoader(BaseLoader):
    """Loader for stock list."""

    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        data_mgr = DataManager()
        list_service = data_mgr.stock.list

        filtered = bool(params.get("filtered", True))
        order_by = str(params.get("order_by", "id"))
        board = params.get("board")
        industry = params.get("industry")

        if board is not None:
            return list_service.load_by_board(board=board, filtered=filtered, order_by=order_by)
        if industry is not None:
            return list_service.load_by_industry(industry=industry, filtered=filtered, order_by=order_by)
        return list_service.load(filtered=filtered, order_by=order_by)
