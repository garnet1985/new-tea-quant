"""IndexWeightDaily Loader。"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence

from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader
from core.modules.data_manager import DataManager


class IndexWeightDailyLoader(BaseDataContractLoader):
    """按指数加载 sys_index_weight（日度权重序列）。"""

    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        dm = DataManager()
        index_service = dm.index
        index_id = self.extract_entity_id(
            params,
            context,
            param_keys=("index_id", "id"),
            context_keys=("index_id", "id", "entity_id"),
            error_msg="加载 index.weight.daily 失败：缺少 index_id（请在 context 中提供）",
        )
        start = params.get("start")
        end = params.get("end")
        return index_service.load_weight(
            index_id=index_id,
            start_date=str(start) if start else None,
            end_date=str(end) if end else None,
        )

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
        context: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        """
        批量加载多个指数的权重数据（逐股查询 - 指数数量通常较少）。

        注意：指数权重数据通常涉及少量指数，暂时采用逐股查询方式。
        后续可根据需要优化为 SQL IN 查询。
        """
        result: Dict[str, Any] = {}
        for eid in entity_ids:
            eid_str = str(eid).strip()
            if not eid_str:
                continue
            ctx = dict(context or {})
            ctx["entity_id"] = eid_str
            ctx["index_id"] = eid_str
            ctx["id"] = eid_str
            try:
                result[eid_str] = self.load(params, ctx)
            except Exception:
                result[eid_str] = []
        return result