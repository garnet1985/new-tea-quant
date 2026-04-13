from __future__ import annotations

from typing import Any, Mapping, Optional

from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_manager import DataManager


class IndexListLoader(BaseLoader):
    """加载全局 sys_index_list。"""

    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        dm = DataManager()
        order_by = str(params.get("order_by", "id"))
        return dm.index.load_list(order_by=order_by)
