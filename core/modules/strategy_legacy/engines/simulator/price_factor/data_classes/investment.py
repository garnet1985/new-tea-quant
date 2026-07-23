#!/usr/bin/env python3
"""Price factor investment model."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.modules.strategy.engines.shared.data_classes import BaseInvestment
from core.modules.strategy.engines.shared.data_classes.investment_state import (
    InvestmentLifecycle,
    InvestmentState,
    PendingExit,
    resolve_outcome,
)
from core.modules.strategy.engines.simulator.price_factor.helpers.holding import (
    latest_executed_exit_date,
    position_fully_closed,
)
from core.modules.strategy.services.data.output.event import parse_opportunity_buy_fill


@dataclass
class PriceFactorInvestment(BaseInvestment):
    tracking: Optional[Dict[str, Any]] = None
    completed_targets: List[Dict[str, Any]] = field(default_factory=list)
    overall_annual_return: float = 0.0
    shares: int = 1
    trigger_date: str = ""
    trigger_price: float = 0.0

    @classmethod
    def from_opportunity(
        cls,
        opportunity: Dict[str, Any],
        targets: List[Dict[str, Any]],
        stock_name: str = "",
        *,
        goal_config: Optional[Dict[str, Any]] = None,
        backtest_calendar: Optional[Any] = None,
        backtest_end_date: str = "",
        pending_exit: Optional[PendingExit] = None,
    ) -> "PriceFactorInvestment":
        opp_id = str(opportunity.get("opportunity_id", "")).strip()
        stock_id = opportunity.get("stock_id", "")
        trigger_date = opportunity.get("trigger_date", "")
        buy_fill = parse_opportunity_buy_fill(opportunity)
        if buy_fill is None:
            raise ValueError(
                f"机会缺少有效 buy_date/buy_price，无法构建 PriceFactorInvestment: {opp_id!r}"
            )
        buy_date, buy_price = buy_fill
        closed = position_fully_closed(targets)
        exit_date = latest_executed_exit_date(targets) if closed else ""

        try:
            trigger_price = float(opportunity.get("trigger_price", 0.0) or 0.0)
        except (ValueError, TypeError):
            trigger_price = 0.0

        profit = sum(float(t.get("weighted_profit", 0.0) or 0.0) for t in targets)
        roi = (profit / buy_price) if buy_price > 0 else 0.0

        from core.modules.strategy.engines.shared.helpers.backtest_calendar_context import (
            BacktestCalendarContext,
            resolve_holding_days,
        )

        exp_cfg = None
        if isinstance(goal_config, dict):
            exp_cfg = goal_config.get("expiration")
        cal_ctx = (
            backtest_calendar
            if isinstance(backtest_calendar, BacktestCalendarContext)
            else BacktestCalendarContext.from_dict(backtest_calendar)
        )
        holding_days = 1
        holding_end = exit_date if closed else (str(backtest_end_date or "").strip() or buy_date)
        if buy_date and holding_end:
            counted = resolve_holding_days(
                buy_date,
                holding_end,
                expiration_config=exp_cfg if isinstance(exp_cfg, dict) else None,
                backtest_calendar=cal_ctx,
            )
            holding_days = max(counted, 1)
        use_trading_days = True
        if isinstance(exp_cfg, dict) and "is_trading_days" in exp_cfg:
            use_trading_days = bool(exp_cfg.get("is_trading_days"))
        overall_annual_return = 0.0
        if holding_days > 0 and closed:
            try:
                from core.modules.strategy.engines.simulator.price_factor.helpers import get_annual_return

                overall_annual_return = get_annual_return(
                    roi, holding_days, is_trading_days=use_trading_days
                )
            except Exception:
                pass

        tracking_exit = exit_date if closed else holding_end
        tracking = cls._build_tracking(opportunity, buy_price, buy_date, tracking_exit)
        completed_targets = cls._build_completed_targets(targets, buy_price)

        if closed:
            state = InvestmentState().complete_with_profit(profit)
        else:
            state = InvestmentState(lifecycle=InvestmentLifecycle.OPEN)
            if pending_exit is not None:
                state = state.mark_pending_exit(pending_exit)

        inv = cls(
            investment_id=f"pf_{opp_id}",
            opportunity_id=opp_id,
            stock_id=stock_id,
            stock_name=stock_name,
            buy_date=buy_date,
            sell_date=exit_date if closed and exit_date else None,
            buy_price=buy_price,
            sell_price=None,
            profit=profit if closed else profit,
            roi=roi if closed else (profit / buy_price if buy_price > 0 and profit else 0.0),
            holding_days=holding_days,
            lifecycle=state.lifecycle.value,
            outcome=state.outcome.value if state.outcome else None,
            pending_exit=state.pending_exit.to_dict() if state.pending_exit else None,
            tracking=tracking,
            completed_targets=completed_targets,
            overall_annual_return=overall_annual_return,
            shares=1,
            trigger_date=trigger_date,
            trigger_price=trigger_price,
        )
        return inv

    @classmethod
    def from_source(cls, source: Any) -> "PriceFactorInvestment":
        if isinstance(source, dict):
            return cls.from_opportunity(
                source.get("opportunity", source),
                source.get("targets", []),
                source.get("stock_name", ""),
            )
        raise ValueError(f"Unsupported source type: {type(source)}")

    @staticmethod
    def _build_tracking(
        opportunity: Dict[str, Any],
        cost_basis: float,
        entry_date: str,
        exit_date: str,
    ) -> Dict[str, Any]:
        try:
            max_price = float(opportunity.get("max_price", 0.0) or 0.0)
        except (ValueError, TypeError):
            max_price = 0.0
        try:
            min_price = float(opportunity.get("min_price", 0.0) or 0.0)
        except (ValueError, TypeError):
            min_price = 0.0
        if cost_basis > 0:
            max_ratio = (max_price - cost_basis) / cost_basis if max_price > 0 else 0.0
            min_ratio = (min_price - cost_basis) / cost_basis if min_price > 0 else 0.0
        else:
            max_ratio = 0.0
            min_ratio = 0.0
        return {
            "max_close_reached": {
                "price": max_price if max_price > 0 else cost_basis,
                "date": exit_date,
                "ratio": max_ratio,
            },
            "min_close_reached": {
                "price": min_price if min_price > 0 else cost_basis,
                "date": entry_date,
                "ratio": min_ratio,
            },
        }

    @staticmethod
    def _build_completed_targets(
        targets: List[Dict[str, Any]],
        cost_basis: float,
    ) -> List[Dict[str, Any]]:
        completed_targets: List[Dict[str, Any]] = []
        for t in targets:
            raw_price = t.get("sell_price")
            if raw_price in (None, ""):
                raw_price = t.get("price")
            if raw_price in (None, ""):
                raw_price = t.get("target_price")
            try:
                sell_price = float(raw_price or 0.0)
            except (TypeError, ValueError):
                sell_price = 0.0
            try:
                profit = float(t.get("profit", 0.0) or 0.0)
            except (TypeError, ValueError):
                profit = 0.0
            try:
                weighted_profit = float(t.get("weighted_profit", 0.0) or 0.0)
            except (TypeError, ValueError):
                weighted_profit = 0.0
            try:
                t_roi = float(t.get("roi", 0.0) or 0.0)
            except (TypeError, ValueError):
                t_roi = 0.0
            try:
                sell_ratio = float(t.get("sell_ratio", 0.0) or 0.0)
            except (TypeError, ValueError):
                sell_ratio = 0.0

            sell_date = t.get("date", "") or t.get("sell_date", "") or t.get("target_date", "") or ""
            reason = (t.get("reason", "") or "").lower()
            if "win" in reason:
                target_type = "take_profit"
                name = reason
            elif "loss" in reason:
                target_type = "stop_loss"
                name = reason
            elif "expiration" in reason:
                target_type = "expired"
                name = "expiration"
            elif "stock_status" in reason:
                target_type = "stock_status"
                name = reason
            else:
                target_type = "unknown"
                name = reason or "unknown"
            completed_targets.append(
                {
                    "name": name,
                    "target_type": target_type,
                    "sell_price": sell_price,
                    "sell_date": sell_date,
                    "sell_ratio": sell_ratio,
                    "profit": profit,
                    "weighted_profit": weighted_profit,
                    "profit_ratio": t_roi,
                    "target_price": cost_basis,
                    "extra_fields": {},
                }
            )
        return completed_targets
