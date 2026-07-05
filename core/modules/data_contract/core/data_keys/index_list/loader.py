"""IndexList Loader。"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader
from core.modules.data_manager import DataManager


class IndexListLoader(BaseDataKeyLoader):
    """加载全局 sys_index_list。"""

    def load(self, params: Mapping[str, Any]) -> Any:
        dm = DataManager()
        order_by = str(params.get("order_by", "id"))
        return dm.index.load_list(order_by=order_by)

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """
        批量加载指数列表数据（GLOBAL scope：所有 entity 共享同一份数据）。
        """
        data = self.load(params)
        return {str(eid).strip(): data for eid in entity_ids if str(eid).strip()}