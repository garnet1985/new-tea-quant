"""StockStPeriodsContract — 查询某股某日 ST / *ST 状态。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from core.modules.data_contract.core.base.base_time_series_contract import (
    BaseTimeSeriesContract,
)
from core.tables.stock.stock_st_periods.st_period_rules import (
    ST_LEVEL_S_STAR_ST,
    ST_LEVEL_SST,
    ST_LEVEL_ST,
    ST_LEVEL_STAR_ST,
    TIER_ST,
    TIER_STAR_ST,
    is_active_on,
    normalize_yyyymmdd,
)

# DB st_level → market_profile / strategy 使用的 status tag
_LEVEL_TO_TAG: Dict[str, str] = {
    ST_LEVEL_ST: TIER_ST,
    ST_LEVEL_SST: TIER_ST,
    ST_LEVEL_STAR_ST: TIER_STAR_ST,
    ST_LEVEL_S_STAR_ST: TIER_STAR_ST,
}


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
        day = normalize_yyyymmdd(trade_date)
        if not day:
            return []
        return self._collect_active_tags(self.periods_for(entity_id), day)

    def level_at(self, entity_id: str, trade_date: str) -> Optional[str]:
        """某日生效的主档标签：``star_st`` | ``st`` | ``None``（*ST 优先）。"""
        tags = self.status_tags_at(entity_id, trade_date)
        if TIER_STAR_ST in tags:
            return TIER_STAR_ST
        if TIER_ST in tags:
            return TIER_ST
        return None

    @staticmethod
    def _collect_active_tags(
        periods: Sequence[Dict[str, Any]],
        trade_date: str,
    ) -> List[str]:
        found = set()
        for row in periods:
            if not is_active_on(row, trade_date):
                continue
            tag = _LEVEL_TO_TAG.get(str(row.get("st_level") or "").strip())
            if tag:
                found.add(tag)
            # 已合并为 tier 名写入的时段（merge_periods_to_tiers）
            level = str(row.get("st_level") or "").strip().lower()
            if level in (TIER_ST, TIER_STAR_ST):
                found.add(level)
        out: List[str] = []
        if TIER_ST in found:
            out.append(TIER_ST)
        if TIER_STAR_ST in found:
            out.append(TIER_STAR_ST)
        return out


__all__ = ["StockStPeriodsContract"]
