"""StockIndicatorsDaily Loader。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.modules.data_contract.core.base.base_loader import BaseDataContractLoader
from core.modules.data_manager import DataManager
from core.infra.utils import Utils
class StockIndicatorsDailyLoader(BaseDataContractLoader):
    """按股票加载 ``sys_stock_indicators`` 日频序列。"""

    def load(self, params: Mapping[str, Any]) -> Any:
        dm = DataManager()
        # 从 params 获取 stock_id
        sid = params.get("stock_id") or params.get("id") or params.get("entity_id")
        if not sid:
            raise ValueError("加载 stock.indicators.daily 失败：缺少 stock_id（请在 params 中提供 stock_id/id/entity_id）")
        sid = str(sid).strip()

        start = Utils.date.normalize_str(params.get("start")) if params.get("start") is not None else None
        end = Utils.date.normalize_str(params.get("end")) if params.get("end") is not None else None
        return dm.stock.indicators.load_range(sid, start_date=start, end_date=end)

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """
        批量加载多个股票的日频指标数据（使用 SQL WHERE IN 优化）。

        Args:
            entity_ids: 股票代码列表
            params: 加载参数（包含 start/end）

        Returns:
            Dict[stock_id, List[Dict]]: 每只股票的指标数据
        """
        ids = [str(x).strip() for x in entity_ids if str(x).strip()]
        if not ids:
            return {}

        dm = DataManager()
        start = Utils.date.normalize_str(params.get("start")) if params.get("start") is not None else None
        end = Utils.date.normalize_str(params.get("end")) if params.get("end") is not None else None

        # 调用 service 层的批量 API
        return dm.stock.indicators.load_batch(
            ids,
            start_date=start,
            end_date=end,
        )