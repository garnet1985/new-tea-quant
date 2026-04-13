from __future__ import annotations

from typing import Any, Mapping, Optional

from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_manager import DataManager


class MacroPmiLoader(BaseLoader):
    """加载全局 sys_pmi（月度序列）。"""

    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        dm = DataManager()
        model = dm.get_table("sys_pmi")
        if not model:
            raise RuntimeError("加载 macro.pmi 失败：未注册 sys_pmi 表")
        return model.load("1=1", order_by="date ASC") or []
