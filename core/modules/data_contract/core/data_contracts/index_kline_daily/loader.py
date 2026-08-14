"""IndexKlineDaily Loader。"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence

from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader
from core.modules.data_manager import DataManager


class IndexKlineDailyLoader(BaseDataContractLoader):
    """按指数加载 sys_index_klines（日线序列）。"""

    def load(self, params: Mapping[str, Any]) -> Any:
        dm = DataManager()
        index_service = dm.index
        # 从 params 获取 index_id
        index_id = params.get("index_id") or params.get("id") or params.get("entity_id")
        if not index_id:
            raise ValueError("加载 index.kline.daily 失败：缺少 index_id（请在 params 中提供 index_id/id/entity_id）")
        index_id = str(index_id).strip()

        start = params.get("start")
        end = params.get("end")
        return index_service.load_indicator(
            index_id=index_id,
            term="daily",
            start_date=str(start) if start else None,
            end_date=str(end) if end else None,
        )

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """
        批量加载多个指数的K线数据（逐股查询 - 指数数量通常较少）。

        注意：指数数据通常涉及少量指数（如 10-50 个），
        暂时采用逐股查询方式。后续可根据需要优化为 SQL IN 查询。
        """
        result: Dict[str, Any] = {}
        for eid in entity_ids:
            eid_str = str(eid).strip()
            if not eid_str:
                continue
            single_params = self.build_batch_load_params(eid_str, params)
            single_params["index_id"] = eid_str  # 添加 index_id 兼容
            try:
                result[eid_str] = self.load(single_params)
            except Exception:
                result[eid_str] = []
        return result