"""申万行业分类 Loader。"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader
from core.modules.data_manager import DataManager


class SwIndustryLoader(BaseDataContractLoader):
    """加载 sys_sw_industry 全部分类。"""

    def load(self, params: Mapping[str, Any]) -> Any:
        return DataManager().sw.load_tree()

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        data = self.load(params)
        return {str(eid).strip(): data for eid in entity_ids if str(eid).strip()}


class SwIndustryListLoader(BaseDataContractLoader):
    """加载有日线的申万实体列表。"""

    def load(self, params: Mapping[str, Any]) -> Any:
        return DataManager().sw.load_quote_list()

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        data = self.load(params)
        return {str(eid).strip(): data for eid in entity_ids if str(eid).strip()}
