"""StockMoneyflowDaily Loader。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.modules.data_contract.core.data_keys.base_loader import BaseDataKeyLoader
from core.modules.data_manager import DataManager
from core.utils.date.date_utils import DateUtils


class StockMoneyflowDailyLoader(BaseDataKeyLoader):
    """按股票加载 ``sys_stock_moneyflow`` 日频序列。"""

    def load(self, params: Mapping[str, Any]) -> Any:
        dm = DataManager()
        # 从 params 获取 stock_id
        sid = params.get("stock_id") or params.get("id") or params.get("entity_id")
        if not sid:
            raise ValueError("加载 stock.moneyflow.daily 失败：缺少 stock_id（请在 params 中提供 stock_id/id/entity_id）")
        sid = str(sid).strip()

        start = DateUtils.normalize_str(params.get("start")) if params.get("start") is not None else None
        end = DateUtils.normalize_str(params.get("end")) if params.get("end") is not None else None
        return dm.stock.moneyflow.load_range(sid, start_date=start, end_date=end)

    def load_batch(
        self,
        entity_ids: Sequence[str],
        params: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """
        批量加载多个股票的资金流向数据（使用 SQL WHERE IN 优化）。

        Args:
            entity_ids: 股票代码列表
            params: 加载参数（包含 start/end）

        Returns:
            Dict[stock_id, List[Dict]]: 每只股票的资金流向数据
        """
        ids = [str(x).strip() for x in entity_ids if str(x).strip()]
        if not ids:
            return {}

        dm = DataManager()
        start = DateUtils.normalize_str(params.get("start")) if params.get("start") is not None else None
        end = DateUtils.normalize_str(params.get("end")) if params.get("end") is not None else None

        # 调用 service 层的批量 API
        return dm.stock.moneyflow.load_batch(
            ids,
            start_date=start,
            end_date=end,
        )