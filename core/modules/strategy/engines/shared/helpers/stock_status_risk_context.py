#!/usr/bin/env python3
"""单股股票状态风控运行时 context（子进程构建，日循环只读）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.modules.strategy.engines.shared.data_classes.strategy_settings.stock_status_risk_settings import (
    StockStatusRiskManagementSettings,
    StockStatusRiskRule,
)
from core.tables.stock.stock_st_periods.st_period_rules import (
    TIER_STAR_ST,
    TIER_ST,
    is_tier_active_on,
    merge_periods_to_tiers,
)


@dataclass(frozen=True)
class StockStatusRiskRuntimeContext:
    """解析后的 goal 规则 + 合并 ST 时段（按回测窗裁剪）。"""

    settings: StockStatusRiskManagementSettings
    tier_periods: Dict[str, List[Dict[str, Any]]]
    stock_meta: Dict[str, Any]

    def needs_st_period_load(self) -> bool:
        return bool(self.settings.rules)

    def active_status_tags_at(self, trade_date: str) -> List[str]:
        """触发日/成交日处于 ST 或 *ST 时段时返回 ``st`` / ``star_st``。"""
        day = str(trade_date or "").strip()
        if not day:
            return []
        tags: List[str] = []
        if self.is_rule_active("st", day):
            tags.append("st")
        if self.is_rule_active("star_st", day):
            tags.append("star_st")
        return tags

    def is_rule_active(self, rule_name: str, trade_date: str) -> bool:
        name = str(rule_name or "").strip().lower()
        if name not in (TIER_ST, TIER_STAR_ST):
            return False
        periods = self.tier_periods.get(name) or []
        return is_tier_active_on(periods, trade_date, tier=name)

    @classmethod
    def build(
        cls,
        *,
        stock_meta: Dict[str, Any],
        settings: StockStatusRiskManagementSettings,
        raw_st_periods: Optional[Sequence[Dict[str, Any]]] = None,
        period_start: str = "",
        period_end: str = "",
    ) -> "StockStatusRiskRuntimeContext":
        tiers: Dict[str, List[Dict[str, Any]]] = {TIER_ST: [], TIER_STAR_ST: []}
        # 始终合并 ST 时段：simulation.skip_investment_when 与枚举打标依赖 tier_periods，
        # 与 goal.stock_status_risk_management 是否配置持仓平仓规则无关。
        if raw_st_periods:
            merged = merge_periods_to_tiers(list(raw_st_periods))
            start = str(period_start or "").strip()
            end = str(period_end or "").strip()
            for tier in (TIER_ST, TIER_STAR_ST):
                tiers[tier] = cls._clip_periods_to_window(
                    merged.get(tier) or [],
                    period_start=start,
                    period_end=end,
                )
        return cls(
            settings=settings,
            tier_periods=tiers,
            stock_meta=dict(stock_meta or {}),
        )

    @staticmethod
    def _clip_periods_to_window(
        periods: List[Dict[str, Any]],
        *,
        period_start: str,
        period_end: str,
    ) -> List[Dict[str, Any]]:
        if not period_start and not period_end:
            return list(periods)
        out: List[Dict[str, Any]] = []
        for row in periods:
            start = str(row.get("start_date") or "")
            end = str(row.get("end_date") or "") or None
            if period_end and start and start > period_end:
                continue
            if period_start and end and end < period_start:
                continue
            clipped = dict(row)
            if period_start and start < period_start:
                clipped["start_date"] = period_start
            if period_end and end and end > period_end:
                clipped["end_date"] = period_end
            out.append(clipped)
        return out


def load_stock_st_periods_for_worker(stock_id: str) -> List[Dict[str, Any]]:
    from core.modules.data_manager import DataManager

    return DataManager(is_verbose=False).stock.st.load_by_stock(str(stock_id).strip())


def build_stock_status_risk_runtime_context(
    *,
    stock_meta: Dict[str, Any],
    settings: StockStatusRiskManagementSettings,
    stock_id: str,
    period_start: str = "",
    period_end: str = "",
) -> StockStatusRiskRuntimeContext:
    raw = load_stock_st_periods_for_worker(stock_id)
    return StockStatusRiskRuntimeContext.build(
        stock_meta=stock_meta,
        settings=settings,
        raw_st_periods=raw,
        period_start=period_start,
        period_end=period_end,
    )


__all__ = [
    "StockStatusRiskRuntimeContext",
    "build_stock_status_risk_runtime_context",
    "load_stock_st_periods_for_worker",
]

