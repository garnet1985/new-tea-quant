"""申万一级行业日线 Loader。"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader
from core.modules.data_manager import DataManager
from core.infra.utils import Utils


class SwIndustryKlineDailyLoader(BaseDataContractLoader):
    """按申万指数代码加载 sys_data_sw_industry_kline。"""

    def load(self, params: Mapping[str, Any]) -> Any:
        industry_id = params.get("industry_id") or params.get("id") or params.get("entity_id")
        if not industry_id:
            raise ValueError("加载 sw.industry.kline.daily 失败：缺少 industry_id")
        start = Utils.date.normalize_str(params.get("start")) if params.get("start") is not None else None
        end = Utils.date.normalize_str(params.get("end")) if params.get("end") is not None else None
        return DataManager().sw.load_kline(str(industry_id).strip(), start_date=start, end_date=end)

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        ids = [str(eid).strip() for eid in entity_ids if str(eid).strip()]
        if not ids:
            return {}
        start = Utils.date.normalize_str(params.get("start")) if params.get("start") is not None else None
        end = Utils.date.normalize_str(params.get("end")) if params.get("end") is not None else None
        return DataManager().sw.load_kline_batch(ids, start_date=start, end_date=end)
