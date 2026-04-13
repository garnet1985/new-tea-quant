from __future__ import annotations

from typing import Any, Mapping, Optional

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
