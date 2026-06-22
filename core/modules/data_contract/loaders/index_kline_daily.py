from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence

from core.modules.data_contract.loaders.base import BaseLoader
from core.modules.data_manager import DataManager


def _index_id(params: Mapping[str, Any], context: Optional[Mapping[str, Any]]) -> str:
    c = context or {}
    idx = params.get("index_id") or params.get("id") or c.get("index_id") or c.get("id") or c.get("entity_id")
    if not idx:
        raise ValueError("加载 index.kline.daily 失败：缺少 index_id（请在 context 中提供）")
    return str(idx)


class IndexKlineDailyLoader(BaseLoader):
    """按指数加载 sys_index_klines（日线序列）。"""

    def load(self, params: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> Any:
        dm = DataManager()
        index_service = dm.index
        index_id = _index_id(params, context)
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
        context: Optional[Mapping[str, Any]] = None,
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
            ctx = dict(context or {})
            ctx["entity_id"] = eid_str
            ctx["index_id"] = eid_str
            ctx["id"] = eid_str
            try:
                result[eid_str] = self.load(params, ctx)
            except Exception:
                result[eid_str] = []
        return result
