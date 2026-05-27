#!/usr/bin/env python3
"""持仓股票状态风控：退市（恒生效）+ goal.stock_status_risk_management 规则。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from core.modules.data_manager.data_services.stock.sub_services.list_service import (
    ListService,
)
from core.modules.strategy.engines.shared.helpers.simulation_pricing import (
    trade_price_defers_to_next_session,
)

if TYPE_CHECKING:
    from core.modules.market_profile.profile import MarketProfile
    from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
        StrategySimulationSettings,
    )
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.stock_status_risk_settings import (
        StockStatusRiskRule,
    )
    from core.modules.strategy.engines.shared.helpers.stock_status_risk_context import (
        StockStatusRiskRuntimeContext,
    )

STOCK_STATUS_REASON_DELISTED = "stock_status:delisted"
STOCK_STATUS_PREFIX = "stock_status:"


def stock_status_reason(name: str) -> str:
    return f"{STOCK_STATUS_PREFIX}{str(name or '').strip().lower()}"


def should_force_exit_delisted(
    stock: Optional[Dict[str, Any]],
    trade_date: str,
) -> bool:
    """``trade_date >= delist_date`` 时触发（与 ``ListService.is_tradable_on`` 一致）。"""
    if not stock:
        return False
    delist = ListService._normalize_delist_date(stock.get("delist_date"))
    if not delist:
        return False
    day = str(trade_date or "").strip()
    if not day:
        return False
    return day >= delist


def price_bar_for_exit(
    current_bar: Dict[str, Any],
    prev_bar: Optional[Dict[str, Any]],
    *,
    mode: str,
) -> Dict[str, Any]:
    if mode == "same_bar_close":
        return current_bar
    if prev_bar:
        return prev_bar
    return current_bar


def _triggered_names(opportunity: "Opportunity") -> List[str]:
    raw = getattr(opportunity, "triggered_stock_status_names", None)
    if not raw:
        return []
    return list(raw)


def _mark_triggered(opportunity: "Opportunity", name: str) -> None:
    names = _triggered_names(opportunity)
    key = str(name or "").strip().lower()
    if key and key not in names:
        names.append(key)
    opportunity.triggered_stock_status_names = names


def _settle_stock_status_exit(
    opportunity: "Opportunity",
    sim: "StrategySimulationSettings",
    price_bar: Dict[str, Any],
    reason: str,
    *,
    sell_ratio: float = 1.0,
    close_invest: bool = True,
    market_profile: Optional["MarketProfile"] = None,
    prev_bar: Optional[Dict[str, Any]] = None,
    status_name: Optional[str] = None,
    stock_status_risk: Optional[Any] = None,
) -> bool:
    if close_invest or sell_ratio >= 1.0:
        ok = opportunity._settle_on_bar(
            sim,
            price_bar,
            reason,
            sell_ratio=1.0,
            market_profile=market_profile,
            prev_bar=prev_bar,
            stock_status_risk=stock_status_risk,
        )
        if ok and status_name:
            _mark_triggered(opportunity, status_name)
        return ok

    if trade_price_defers_to_next_session(sim.sell_price_model):
        opportunity._defer_exit(reason, sell_ratio=sell_ratio)
        return opportunity.pending_exit is None

    exit_px = opportunity._exit_price(sim, price_bar)
    if exit_px is None:
        return False
    basis = opportunity._cost_basis()
    current_date = str(price_bar.get("date") or "")
    price_return = (exit_px - basis) / basis if basis > 0 else 0.0
    profit = exit_px - basis
    weighted_profit = profit * sell_ratio
    if not opportunity.completed_targets:
        opportunity.completed_targets = []
    target_entry = {
        "date": current_date,
        "price": exit_px,
        "reason": reason,
        "roi": price_return,
        "sell_ratio": sell_ratio,
        "profit": profit,
        "weighted_profit": weighted_profit,
    }
    if market_profile is not None:
        from core.modules.strategy.engines.shared.helpers.tradability import (
            stamp_target_tradability,
        )

        stamp_target_tradability(
            target_entry,
            market_profile,
            opportunity.stock_id,
            prev_bar,
            exit_px,
            stock_status_risk=stock_status_risk,
            trade_date=current_date,
            exec_bar=price_bar,
        )
    opportunity.completed_targets.append(target_entry)
    total_weighted = sum(
        float(t.get("weighted_profit", 0) or 0) for t in opportunity.completed_targets
    )
    opportunity.roi = total_weighted / basis if basis > 0 else 0.0
    total_ratio = sum(float(t.get("sell_ratio", 0) or 0) for t in opportunity.completed_targets)
    from core.modules.strategy.enums import OpportunityStatus

    if total_ratio >= 1.0:
        opportunity.status = (
            OpportunityStatus.WIN.value if (opportunity.roi or 0) > 0 else OpportunityStatus.LOSS.value
        )
        opportunity.sell_date = current_date
        opportunity.sell_price = exit_px
        opportunity.sell_reason = reason
    else:
        opportunity.status = OpportunityStatus.OPEN.value
    if status_name:
        _mark_triggered(opportunity, status_name)
    return opportunity.pending_exit is None


def apply_stock_status_risk_management(
    opportunity: "Opportunity",
    sim: "StrategySimulationSettings",
    current_bar: Dict[str, Any],
    ctx: "StockStatusRiskRuntimeContext",
    *,
    prev_bar: Optional[Dict[str, Any]] = None,
    market_profile: Optional["MarketProfile"] = None,
    stock: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    先退市（不可配置关闭），再按 goal.rules 处理 st / star_st（各规则仅触发一次）。
    返回是否已完成全平（无 pending_exit）。
    """
    meta = stock if stock is not None else (opportunity.stock or ctx.stock_meta)
    current_date = str(current_bar.get("date") or "")

    if should_force_exit_delisted(meta, current_date):
        mode = ctx.settings.delisted_exit_price
        bar = price_bar_for_exit(current_bar, prev_bar, mode=mode)
        if _settle_stock_status_exit(
            opportunity,
            sim,
            bar,
            STOCK_STATUS_REASON_DELISTED,
            sell_ratio=1.0,
            close_invest=True,
            market_profile=market_profile,
            prev_bar=prev_bar,
            stock_status_risk=ctx,
        ):
            return opportunity.pending_exit is None

    for rule in ctx.settings.rules:
        if not _should_apply_rule(opportunity, rule, ctx, current_date):
            continue
        reason = stock_status_reason(rule.name)
        if _settle_stock_status_exit(
            opportunity,
            sim,
            current_bar,
            reason,
            sell_ratio=rule.sell_ratio,
            close_invest=rule.close_invest,
            market_profile=market_profile,
            prev_bar=prev_bar,
            status_name=rule.name,
            stock_status_risk=ctx,
        ):
            if rule.close_invest or rule.sell_ratio >= 1.0:
                return opportunity.pending_exit is None
    return False


def _should_apply_rule(
    opportunity: "Opportunity",
    rule: "StockStatusRiskRule",
    ctx: "StockStatusRiskRuntimeContext",
    trade_date: str,
) -> bool:
    name = str(rule.name or "").strip().lower()
    if name in _triggered_names(opportunity):
        return False
    return ctx.is_rule_active(name, trade_date)


def apply_stock_status_risk_management_from_settings(
    opportunity: "Opportunity",
    sim: "StrategySimulationSettings",
    current_bar: Dict[str, Any],
    *,
    stock_status_risk: Optional["StockStatusRiskRuntimeContext"] = None,
    prev_bar: Optional[Dict[str, Any]] = None,
    market_profile: Optional["MarketProfile"] = None,
    stock: Optional[Dict[str, Any]] = None,
) -> bool:
    if stock_status_risk is None:
        from core.modules.strategy.engines.shared.data_classes.strategy_settings.stock_status_risk_settings import (
            StockStatusRiskManagementSettings,
        )
        from core.modules.strategy.engines.shared.helpers.stock_status_risk_context import (
            StockStatusRiskRuntimeContext,
            build_stock_status_risk_runtime_context,
        )

        settings = StockStatusRiskManagementSettings.from_goal_block(None)
        stock_meta = stock or opportunity.stock or {}
        if settings.rules:
            sid = str(stock_meta.get("id") or opportunity.stock_id or "").strip()
            stock_status_risk = build_stock_status_risk_runtime_context(
                stock_meta=stock_meta,
                settings=settings,
                stock_id=sid,
            )
        else:
            stock_status_risk = StockStatusRiskRuntimeContext.build(
                stock_meta=stock_meta,
                settings=settings,
            )
    return apply_stock_status_risk_management(
        opportunity,
        sim,
        current_bar,
        stock_status_risk,
        prev_bar=prev_bar,
        market_profile=market_profile,
        stock=stock,
    )

def last_tradable_bar_for_delist(
    current_bar: Dict[str, Any],
    prev_bar: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    return price_bar_for_exit(current_bar, prev_bar, mode="last_tradable_close")


__all__ = [
    "STOCK_STATUS_PREFIX",
    "STOCK_STATUS_REASON_DELISTED",
    "apply_stock_status_risk_management",
    "apply_stock_status_risk_management_from_settings",
    "last_tradable_bar_for_delist",
    "price_bar_for_exit",
    "should_force_exit_delisted",
    "stock_status_reason",
]
