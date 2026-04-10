from __future__ import annotations

from typing import Any, Mapping, Optional

from core.modules.data_contract.contract_const import DataKey
from core.modules.data_contract.loaders.base import BaseLoader


class StockListLoader(BaseLoader):
    """Loader for stock list."""

    data_id = DataKey.STOCK_LIST

    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        # TODO: implement actual DataManager call.
        raise NotImplementedError("StockListLoader.load 尚未实现")
