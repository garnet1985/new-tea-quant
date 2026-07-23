"""StockCorporateFinance Loader。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader
from core.modules.data_manager import DataManager


class StockCorporateFinanceLoader(BaseDataContractLoader):
    """按股票加载 sys_corporate_finance（季度序列）。"""

    def load(self, params: Mapping[str, Any]) -> Any:
        dm = DataManager()
        # 从 params 获取 stock_id
        sid = params.get("stock_id") or params.get("id") or params.get("entity_id")
        if not sid:
            raise ValueError("加载 corporate finance 失败：缺少 stock_id（请在 params 中提供 stock_id/id/entity_id）")
        sid = str(sid).strip()

        # 使用极宽季度范围等价于"全量季度序列"
        return dm.stock.corporate_finance.load_trend(
            sid,
            start_quarter="0000Q1",
            end_quarter="9999Q4",
        )

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """
        批量加载多个股票的企业财务数据（逐股查询 - 季度数据量小，性能影响有限）。

        注意：企业财务数据通常按季度更新，数据量较小，
        暂时采用逐股查询方式。后续可根据需要优化为真正的 SQL IN 查询。
        """
        result: Dict[str, Any] = {}
        for eid in entity_ids:
            eid_str = str(eid).strip()
            if not eid_str:
                continue
            single_params = self.build_batch_load_params(eid_str, params)
            try:
                result[eid_str] = self.load(single_params)
            except Exception:
                result[eid_str] = []
        return result