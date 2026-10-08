"""StockStPeriodsContract — 查询某股某日 ST / *ST 状态。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.modules.data_contract.core.base.base_time_series_contract import (
    BaseTimeSeriesContract,
)
from core.tables.stock.stock_st_periods.st_period_rules import (
    TIER_ST,
    TIER_STAR_ST,
    active_status_tags,
)


class StockStPeriodsContract(BaseTimeSeriesContract):
    """ST 时段 contract：稀疏区间时序，数据为 ``Dict[entity_id, List[period_row]]``。

    消费主路径是 ``status_tags_at`` / ``level_at``（按区间判定），不是日频 cursor 推进。
    时间轴字段为 ``start_date``（区间起点）。
    """

    def get_base_time_field(self) -> Optional[str]:
        if self.runtime.base_time_field:
            return self.runtime.base_time_field
        return "start_date"

    def periods_for(self, entity_id: str) -> List[Dict[str, Any]]:
        """返回某股已加载的原始时段行（可能为空）。"""
        eid = str(entity_id or "").strip()
        if not eid:
            return []
        raw = self.get_entity_data(eid)
        if raw is None:
            return []
        if isinstance(raw, list):
            return list(raw)
        return []

    def status_tags_at(self, entity_id: str, trade_date: str) -> List[str]:
        """某日生效标签列表（供 ``is_at_limit_*`` / skip 使用）。

        可能同时含 ``st`` 与 ``star_st``（重叠时段）；顺序：``st`` 先、``star_st`` 后。
        """
        return active_status_tags(self.periods_for(entity_id), trade_date)

    def level_at(self, entity_id: str, trade_date: str) -> Optional[str]:
        """某日生效的主档标签：``star_st`` | ``st`` | ``None``（*ST 优先）。"""
        tags = self.status_tags_at(entity_id, trade_date)
        if TIER_STAR_ST in tags:
            return TIER_STAR_ST
        if TIER_ST in tags:
            return TIER_ST
        return None


__all__ = ["StockStPeriodsContract"]
