"""Stock ST periods Loader — ``sys_stock_st_periods``。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader
from core.modules.data_manager import DataManager
from core.tables.stock.stock_st_periods.st_period_rules import normalize_yyyymmdd


class StockStPeriodsLoader(BaseDataContractLoader):
    """按股加载 ST / *ST 警示时段（稀疏区间，非 K 线）。

    params 约定（与 ``BaseDataContractLoader`` 一致）：
    - ``load``：必须含 ``entity_id``；可选 ``start`` / ``end``
    - ``load_batch``：``entity_ids`` 与 params 分离；params 仅含 ``start`` / ``end`` 等
    """

    def load(self, params: Mapping[str, Any]) -> List[Dict[str, Any]]:
        entity_id = params.get("entity_id")
        if entity_id is None or not str(entity_id).strip():
            raise ValueError("加载 stock.st_periods 失败：缺少 entity_id")
        entity_id = str(entity_id).strip()
        dm = DataManager()
        rows = dm.stock.st.load_by_stock(entity_id)
        return self._clip_to_window(rows, params)

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
    ) -> Mapping[str, List[Dict[str, Any]]]:
        ids = [str(x).strip() for x in entity_ids if str(x).strip()]
        if not ids:
            return {}

        start = normalize_yyyymmdd(params.get("start") or "")
        end = normalize_yyyymmdd(params.get("end") or "")
        dm = DataManager()

        if start and end:
            grouped = dm.stock.st.load_overlapping(
                ids, period_start=start, period_end=end
            )
        else:
            grouped = {sid: dm.stock.st.load_by_stock(sid) for sid in ids}

        out: Dict[str, List[Dict[str, Any]]] = {}
        for sid in ids:
            out[sid] = self._clip_to_window(list(grouped.get(sid) or []), params)
        return out

    @staticmethod
    def _clip_to_window(
        rows: List[Dict[str, Any]],
        params: Mapping[str, Any],
    ) -> List[Dict[str, Any]]:
        start = normalize_yyyymmdd(params.get("start") or "")
        end = normalize_yyyymmdd(params.get("end") or "")
        if not start and not end:
            return list(rows)
        clipped: List[Dict[str, Any]] = []
        for row in rows:
            row_start = normalize_yyyymmdd(row.get("start_date"))
            row_end = normalize_yyyymmdd(row.get("end_date")) or None
            if end and row_start and row_start > end:
                continue
            if start and row_end and row_end < start:
                continue
            item = dict(row)
            if start and row_start and row_start < start:
                item["start_date"] = start
            if end and row_end and row_end > end:
                item["end_date"] = end
            clipped.append(item)
        return clipped


__all__ = ["StockStPeriodsLoader"]
