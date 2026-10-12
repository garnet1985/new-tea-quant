"""股票申万行业 Loader。"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader
from core.modules.data_manager import DataManager


class StockSwIndustryLoader(BaseDataContractLoader):
    """按股票加载当前申万一、二、三级。"""

    def load(self, params: Mapping[str, Any]) -> Any:
        stock_id = params.get("stock_id") or params.get("id") or params.get("entity_id")
        if not stock_id:
            raise ValueError("加载 stock.sw_industry 失败：缺少 stock_id")
        return DataManager().sw.load_stock_industry(str(stock_id).strip())

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        ids = [str(eid).strip() for eid in entity_ids if str(eid).strip()]
        if not ids:
            return {}
        return DataManager().sw.load_stock_industry_batch(ids)
