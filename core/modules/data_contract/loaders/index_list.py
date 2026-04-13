from __future__ import annotations

from typing import Any, Mapping, Optional

from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_manager import DataManager


class IndexListLoader(BaseLoader):
    """加载全局 sys_index_list。"""

    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        dm = DataManager()
        model = dm.get_table("sys_index_list")
        if not model:
            raise RuntimeError("加载 index.list 失败：未注册 sys_index_list 表")
        order_by = str(params.get("order_by", "id"))
        return model.load("1=1", order_by=order_by) or []
