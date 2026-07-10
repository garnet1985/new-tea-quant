"""Investment — trading state and exit logic built on top of ``Opportunity``.

Naming:
- ``settings.goal`` / ``check_goals``: exit rules from strategy config.
- ``completed_goals``: one row per partial or full exit leg.
- ``entry_*`` / ``exit_*`` / ``direction``: direction-neutral trade fields.
- ``outcome``: aggregated investment output; ``outcome.result`` is win/loss.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.modules.strategy.core.engines.shared.data_class.opportunity import (
    Opportunity,
    OpportunityContributor,
    OpportunityMeta,
)


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class Lifecycle(str, Enum):
    OPEN = "open"
    PENDING_TO_BUY = "pending_to_buy"
    PENDING_TO_SELL = "pending_to_sell"
    COMPLETE = "complete"


class ExitReason(str, Enum):
    EXPIRED = "expired"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    SIMULATE_END = "simulate_end"


class InvestmentResult(str, Enum):
    WIN = "win"
    LOSS = "loss"


class ExpirationMode(str, Enum):
    """持有期计数方式。"""
    NATURAL_DAY = "natural_day"  # 自然日：日历日差
    TRADING_DAY = "trading_day"  # 交易日：随 K 线推进，仅在开市日累加
    OPEN_DAY = "open_day"  # 开盘日：日历上 [entry, current] 开市日个数（含端点）


@dataclass(frozen=True)
class ExpirationRule:
    window_days: int
    mode: ExpirationMode


@dataclass
class EntryInfo:
    entry_price: float = 0.0
    entry_date: str = ""
    direction: TradeSide = TradeSide.BUY


@dataclass
class ExitInfo:
    exit_price: Optional[float] = None
    exit_date: str = ""
    exit_reason: str = ""
    exit_ratio: float = 0.0


@dataclass
class PendingExit:
    reason: str = ""
    exit_ratio: float = 1.0


@dataclass
class HoldingState:
    """持有期快照与交易日历驱动的计数状态。"""
    mode: Optional[ExpirationMode] = None
    window_days: int = 0
    days: int = 0
    last_bar_date: str = ""
    trading_day_count: int = 0
    counter_initialized: bool = False


@dataclass
class ExtremePriceEdge:
    highest: Optional[float] = None
    lowest: Optional[float] = None
    highest_date: str = ""
    lowest_date: str = ""
    highest_return: Optional[float] = None
    lowest_return: Optional[float] = None


@dataclass
class RiskState:
    protect_loss_active: bool = False
    dynamic_loss_active: bool = False
    dynamic_loss_peak: Optional[float] = None
    triggered_stop_loss_idx: int = -1
    triggered_take_profit_idx: int = -1


@dataclass
class OutcomePerformance:
    result: Optional[InvestmentResult] = None
    weighted_roi: float = 0.0
    price_return: Optional[float] = None
    max_drawdown: Optional[float] = None


@dataclass
class GoalCheckingSteps(Enum):
    CHECK_STOP_LOSS = "check_stop_loss"
    CHECK_TAKE_PROFIT = "check_take_profit"
    CHECK_EXPIRATION = "check_expiration"


@dataclass
class Investment(Opportunity):
    """Extends ``Opportunity`` with grouped, direction-neutral trading state."""

    lifecycle: Lifecycle = Lifecycle.PENDING_TO_BUY
    entry: EntryInfo = field(default_factory=EntryInfo)
    exit: ExitInfo = field(default_factory=ExitInfo)
    pending_exit: Optional[PendingExit] = None
    holding: HoldingState = field(default_factory=HoldingState)
    extreme: ExtremePriceEdge = field(default_factory=ExtremePriceEdge)
    risk: RiskState = field(default_factory=RiskState)
    outcome: OutcomePerformance = field(default_factory=OutcomePerformance)
    completed_goals: List[Dict[str, Any]] = field(default_factory=list)

    goal_checking_pipeline: List[GoalCheckingSteps] = [
        GoalCheckingSteps.CHECK_STOP_LOSS, 
        GoalCheckingSteps.CHECK_TAKE_PROFIT, 
        GoalCheckingSteps.CHECK_EXPIRATION
    ]

    # *************************************
    #             投资目标检查 
    # *************************************
    def _resolve_goal_checking_pipeline(self) -> List[GoalCheckingSteps]:
        pipeline = []
        # TODO: resolve pipeline based on simulation settings
        return pipeline

    def check_goals(self) -> bool:

        for step in self.goal_checking_pipeline:
            if step == GoalCheckingSteps.CHECK_STOP_LOSS:
                if self.check_stop_loss():
                    return True
            elif step == GoalCheckingSteps.CHECK_TAKE_PROFIT:
                if self.check_take_profit():
                    return True
            elif step == GoalCheckingSteps.CHECK_EXPIRATION:
                if self.check_expiration():
                    return True

        return False

    def _check_stop_loss(self) -> bool:
        # TODO: check stop loss
        # step 1: check stop loss
        # step 2: check protect loss
        # step 3: check dynamic loss
        return False

    def _check_take_profit(self) -> bool:
        # TODO: check take profit
        return False

    def _check_expiration(self) -> bool:
        # TODO: check expiration
        return False

    # *************************************
    #             投资入场
    # *************************************

    def enter(self) -> bool:
        # TODO: enter
        return False


    # *************************************
    #             投资结算
    # *************************************

    def exit(self) -> bool:
        # TODO: exit
        return False


    def settle(self) -> bool:
        # TODO: settle
        return False


__all__ = [
    "EntryInfo",
    "ExitInfo",
    "ExitReason",
    "ExpirationMode",
    "ExpirationRule",
    "ExtremePriceEdge",
    "GoalCheckingSteps",
    "HoldingState",
    "Investment",
    "InvestmentResult",
    "Lifecycle",
    "OutcomePerformance",
    "PendingExit",
    "RiskState",
    "TradeSide",
]


#     def _close_side(self) -> TradeSide:
#         return TradeSide.SELL if self.trade.entry.direction == TradeSide.BUY else TradeSide.BUY

#     def _directional_return(self, price: float, basis: float) -> float:
#         if basis <= 0:
#             return 0.0
#         if self.trade.entry.direction == TradeSide.SELL:
#             return (basis - price) / basis
#         return (price - basis) / basis

#     def _directional_profit(self, exit_price: float, basis: float) -> float:
#         if self.trade.entry.direction == TradeSide.SELL:
#             return basis - exit_price
#         return exit_price - basis

#     def _cost_basis(self) -> float:
#         return float(self.trade.entry.entry_price or 0.0)

#     def _exit_price(self, sim: Any, bar: Dict[str, Any]) -> Optional[float]:
#         close_side = self._close_side()
#         exit_price_model = getattr(sim, "exit_price_model", getattr(sim, "sell_price_model", None))
#         entry_price_model = getattr(sim, "entry_price_model", getattr(sim, "buy_price_model", exit_price_model))
#         raw = self._trade_theoretical_price_on_bar(
#             exit_price_model if close_side == TradeSide.SELL else entry_price_model,
#             side=close_side.value,
#             bar=bar,
#         )
#         if raw is None:
#             return None
#         return self._apply_exit_slippage(sim, raw, close_side)

#     def _apply_exit_slippage(self, sim: Any, price: float, close_side: TradeSide) -> float:
#         if close_side == TradeSide.SELL:
#             bps = float(getattr(sim, "slippage_exit_bps", getattr(sim, "slippage_sell_bps", 0.0)) or 0.0)
#             return float(price) * (1.0 - max(0.0, bps) / 10_000.0)
#         bps = float(getattr(sim, "slippage_entry_bps", getattr(sim, "slippage_buy_bps", getattr(sim, "slippage_sell_bps", 0.0))) or 0.0)
#         return float(price) * (1.0 + max(0.0, bps) / 10_000.0)

#     # --- settlement ---

#     def _settle_on_bar(
#         self,
#         sim: Any,
#         bar: Dict[str, Any],
#         reason: str,
#         *,
#         exit_ratio: float = 1.0,
#         market_profile: Optional[Any] = None,
#         prev_bar: Optional[Dict[str, Any]] = None,
#         stock_status_risk: Optional[Any] = None,
#     ) -> bool:
#         exit_px = self._exit_price(sim, bar)
#         if exit_px is None:
#             return False
#         basis = self._cost_basis()
#         price_return = self._directional_return(exit_px, basis)
#         self._settle(
#             bar["date"],
#             exit_px,
#             reason,
#             price_return,
#             exit_ratio=exit_ratio,
#             market_profile=market_profile,
#             prev_bar=prev_bar,
#             stock_status_risk=stock_status_risk,
#             exec_bar=bar,
#         )
#         return True

#     def _defer_exit(self, reason: str, *, exit_ratio: float = 1.0) -> bool:
#         self.trade.pending_exit = PendingExit(reason=reason, exit_ratio=exit_ratio)
#         self.trade.lifecycle = Lifecycle.PENDING_TO_SELL
#         return True

#     def _request_exit(
#         self,
#         sim: Any,
#         bar: Dict[str, Any],
#         reason: str,
#         *,
#         exit_ratio: float = 1.0,
#         market_profile: Optional[Any] = None,
#         prev_bar: Optional[Dict[str, Any]] = None,
#         stock_status_risk: Optional[Any] = None,
#     ) -> bool:
#         exit_price_model = getattr(sim, "exit_price_model", getattr(sim, "sell_price_model", None))
#         entry_price_model = getattr(sim, "entry_price_model", getattr(sim, "buy_price_model", exit_price_model))
#         exit_model = exit_price_model if self._close_side() == TradeSide.SELL else entry_price_model
#         if self._trade_price_defers_to_next_session(exit_model):
#             return self._defer_exit(reason, exit_ratio=exit_ratio)
#         return self._settle_on_bar(
#             sim,
#             bar,
#             reason,
#             exit_ratio=exit_ratio,
#             market_profile=market_profile,
#             prev_bar=prev_bar,
#             stock_status_risk=stock_status_risk,
#         )

#     def execute_pending_exit(
#         self,
#         sim: Any,
#         bar: Dict[str, Any],
#         *,
#         market_profile: Optional[Any] = None,
#         prev_bar: Optional[Dict[str, Any]] = None,
#         stock_status_risk: Optional[Any] = None,
#     ) -> bool:
#         if self.trade.pending_exit is None:
#             return False
#         pending = self.trade.pending_exit
#         self.trade.pending_exit = None
#         settled = self._settle_on_bar(
#             sim,
#             bar,
#             pending.reason or "exit",
#             exit_ratio=float(pending.exit_ratio or 1.0),
#             market_profile=market_profile,
#             prev_bar=prev_bar,
#             stock_status_risk=stock_status_risk,
#         )
#         return settled and self.is_complete()

#     def is_valid(self) -> bool:
#         return self.trade.lifecycle == Lifecycle.OPEN and bool(self.trade.entry.entry_date)

#     def is_complete(self) -> bool:
#         return self.trade.lifecycle == Lifecycle.COMPLETE

#     def calculate_annual_return(self) -> float:
#         if not self.trade.outcome.price_return or not self.trade.holding.days:
#             return 0.0
#         return self.trade.outcome.price_return * (250 / self.trade.holding.days)

#     def settle(
#         self,
#         sim: Any,
#         last_kline: Dict[str, Any],
#         reason: str = ExitReason.SIMULATE_END.value,
#         *,
#         market_profile: Optional[Any] = None,
#         prev_bar: Optional[Dict[str, Any]] = None,
#         stock_status_risk: Optional[Any] = None,
#     ) -> None:
#         exit_price_model = getattr(sim, "exit_price_model", getattr(sim, "sell_price_model", None))
#         entry_price_model = getattr(sim, "entry_price_model", getattr(sim, "buy_price_model", exit_price_model))
#         exit_model = exit_price_model if self._close_side() == TradeSide.SELL else entry_price_model
#         if self.trade.pending_exit and self._trade_price_defers_to_next_session(exit_model):
#             pending = self.trade.pending_exit
#             self.trade.pending_exit = None
#             self._settle_on_bar(
#                 sim,
#                 last_kline,
#                 pending.reason or reason,
#                 exit_ratio=float(pending.exit_ratio or 1.0),
#                 market_profile=market_profile,
#                 prev_bar=prev_bar,
#                 stock_status_risk=stock_status_risk,
#             )
#             return
#         self._settle_on_bar(
#             sim,
#             last_kline,
#             reason,
#             exit_ratio=1.0,
#             market_profile=market_profile,
#             prev_bar=prev_bar,
#             stock_status_risk=stock_status_risk,
#         )

#     # --- goal checking ---

#     def check_goals(
#         self,
#         sim: Any,
#         current_kline: Dict[str, Any],
#         goal_config: Dict[str, Any],
#         *,
#         market_profile: Optional[Any] = None,
#         prev_bar: Optional[Dict[str, Any]] = None,
#         backtest_calendar: Optional[Any] = None,
#         stock_status_risk: Optional[Any] = None,
#     ) -> bool:
#         current_price = self._monitor_bar_price(current_kline, sim.monitor_price_model)
#         current_date = str(current_kline["date"])
#         basis = self._cost_basis()

#         if not self.trade.entry.entry_date:
#             return False

#         if market_profile is not None and hasattr(market_profile, "sell_blocked_by_settlement"):
#             if market_profile.sell_blocked_by_settlement(
#                 buy_date=self.trade.entry.entry_date,
#                 trade_date=current_date,
#                 backtest_calendar=backtest_calendar,
#             ):
#                 return False

#         if stock_status_risk is not None:
#             if self._apply_stock_status_risk_management(
#                 sim,
#                 current_kline,
#                 stock_status_risk,
#                 prev_bar=prev_bar,
#                 market_profile=market_profile,
#             ):
#                 return self.trade.pending_exit is None
#         elif self._apply_stock_status_risk_management_from_settings(
#             sim,
#             current_kline,
#             prev_bar=prev_bar,
#             market_profile=market_profile,
#         ):
#             return self.trade.pending_exit is None

#         price_return = self._directional_return(current_price, basis)
#         self._track_extreme(current_price, current_date, basis)

#         calendar = self._calendar_from_raw(backtest_calendar)
#         for rule in self._parse_expiration_rules(goal_config):
#             held = self._holding_days(current_date, rule, calendar=calendar)
#             self.trade.holding.mode = rule.mode
#             self.trade.holding.window_days = rule.window_days
#             self.trade.holding.days = held
#             if held >= rule.window_days:
#                 if self._request_exit(
#                     sim,
#                     current_kline,
#                     ExitReason.EXPIRED.value,
#                     exit_ratio=1.0,
#                     market_profile=market_profile,
#                     prev_bar=prev_bar,
#                     stock_status_risk=stock_status_risk,
#                 ):
#                     return self.trade.pending_exit is None

#         if self.trade.risk.protect_loss_active:
#             protect_ratio = goal_config.get("protect_loss", {}).get("ratio", 0)
#             if price_return <= protect_ratio:
#                 if self._request_exit(
#                     sim,
#                     current_kline,
#                     "protect_loss",
#                     exit_ratio=1.0,
#                     market_profile=market_profile,
#                     prev_bar=prev_bar,
#                     stock_status_risk=stock_status_risk,
#                 ):
#                     return self.trade.pending_exit is None

#         if self.trade.risk.dynamic_loss_active:
#             dynamic_ratio = goal_config.get("dynamic_loss", {}).get("ratio", -0.1)
#             peak = self.trade.risk.dynamic_loss_peak
#             if peak is None:
#                 peak = basis
#             if self.trade.entry.direction == TradeSide.SELL:
#                 peak = min(peak, current_price)
#                 drawdown = (current_price - peak) / peak if peak else 0.0
#             else:
#                 peak = max(peak, current_price)
#                 drawdown = (current_price - peak) / peak if peak else 0.0
#             self.trade.risk.dynamic_loss_peak = peak
#             if drawdown <= dynamic_ratio:
#                 if self._request_exit(
#                     sim,
#                     current_kline,
#                     "dynamic_loss",
#                     exit_ratio=1.0,
#                     market_profile=market_profile,
#                     prev_bar=prev_bar,
#                     stock_status_risk=stock_status_risk,
#                 ):
#                     return self.trade.pending_exit is None

#         for idx, stage in enumerate(goal_config.get("stop_loss", {}).get("stages", [])):
#             if idx <= self.trade.risk.triggered_stop_loss_idx:
#                 continue
#             stage_ratio = stage.get("ratio", 0)
#             if price_return <= stage_ratio:
#                 self.trade.risk.triggered_stop_loss_idx = idx
#                 if stage.get("close_invest", False):
#                     stage_name = stage.get("name")
#                     reason = stage_name or f"{ExitReason.STOP_LOSS.value}_{int(stage_ratio * 100)}%"
#                     if self._request_exit(
#                         sim,
#                         current_kline,
#                         reason,
#                         exit_ratio=1.0,
#                         market_profile=market_profile,
#                         prev_bar=prev_bar,
#                         stock_status_risk=stock_status_risk,
#                     ):
#                         return self.trade.pending_exit is None

#         for idx, stage in enumerate(goal_config.get("take_profit", {}).get("stages", [])):
#             if idx <= self.trade.risk.triggered_take_profit_idx:
#                 continue
#             stage_ratio = stage.get("ratio", 0)
#             if price_return >= stage_ratio:
#                 self.trade.risk.triggered_take_profit_idx = idx
#                 actions = stage.get("actions", [])
#                 if "set_protect_loss" in actions:
#                     self.trade.risk.protect_loss_active = True
#                 if "set_dynamic_loss" in actions:
#                     self.trade.risk.dynamic_loss_active = True
#                     self.trade.risk.dynamic_loss_peak = current_price

#                 stage_name = stage.get("name")
#                 reason = stage_name or f"{ExitReason.TAKE_PROFIT.value}_{int(stage_ratio * 100)}%"

#                 if stage.get("close_invest", False):
#                     if self._request_exit(
#                         sim,
#                         current_kline,
#                         reason,
#                         exit_ratio=1.0,
#                         market_profile=market_profile,
#                         prev_bar=prev_bar,
#                         stock_status_risk=stock_status_risk,
#                     ):
#                         return self.trade.pending_exit is None

#                 exit_ratio = float(stage.get("exit_ratio", stage.get("sell_ratio", 1.0)))
#                 exit_price_model = getattr(sim, "exit_price_model", getattr(sim, "sell_price_model", None))
#                 entry_price_model = getattr(sim, "entry_price_model", getattr(sim, "buy_price_model", exit_price_model))
#                 exit_model = exit_price_model if self._close_side() == TradeSide.SELL else entry_price_model
#                 if self._trade_price_defers_to_next_session(exit_model):
#                     self._defer_exit(reason, exit_ratio=exit_ratio)
#                     continue
#                 exit_px = self._exit_price(sim, current_kline)
#                 if exit_px is None:
#                     continue
#                 profit = self._directional_profit(exit_px, basis)
#                 goal_entry = {
#                     "opportunity_id": self.meta.opportunity_id,
#                     "date": current_date,
#                     "direction": self.entry.direction.value,
#                     "entry_price": basis,
#                     "exit_price": exit_px,
#                     "reason": reason,
#                     "roi": price_return,
#                     "exit_ratio": exit_ratio,
#                     "profit": profit,
#                     "weighted_profit": profit * exit_ratio,
#                 }
#                 if market_profile is not None:
#                     self._stamp_goal_tradability(
#                         goal_entry,
#                         market_profile,
#                         prev_bar,
#                         exit_px,
#                         stock_status_risk=stock_status_risk,
#                         trade_date=current_date,
#                         exec_bar=current_kline,
#                     )
#                 self.trade.completed_goals.append(goal_entry)
#                 total_weighted = sum(
#                     float(t.get("weighted_profit", 0) or 0) for t in self.trade.completed_goals
#                 )
#                 if self._apply_partial_or_complete(
#                     total_weighted, basis, current_date, exit_px, reason
#                 ):
#                     return True

#         return False

#     def _track_extreme(self, current_price: float, current_date: str, basis: float) -> None:
#         extreme = self.trade.extreme
#         if extreme.highest is None or current_price > extreme.highest:
#             extreme.highest = current_price
#             extreme.highest_date = current_date
#         if extreme.lowest is None or current_price < extreme.lowest:
#             extreme.lowest = current_price
#             extreme.lowest_date = current_date
#         if basis > 0:
#             if extreme.highest is not None:
#                 extreme.highest_return = self._directional_return(extreme.highest, basis)
#             if extreme.lowest is not None:
#                 extreme.lowest_return = self._directional_return(extreme.lowest, basis)

#     def _apply_partial_or_complete(
#         self,
#         total_weighted_profit: float,
#         basis: float,
#         current_date: str,
#         exit_px: float,
#         reason: str,
#     ) -> bool:
#         self.trade.outcome.weighted_roi = total_weighted_profit / basis if basis > 0 else 0.0
#         total_ratio = sum(
#             float(t.get("exit_ratio", t.get("sell_ratio", 0)) or 0)
#             for t in self.trade.completed_goals
#         )
#         if total_ratio >= 1.0:
#             self.trade.lifecycle = Lifecycle.COMPLETE
#             self.trade.outcome.result = self._resolve_result(total_weighted_profit)
#             self.trade.exit.exit_date = current_date
#             self.trade.exit.exit_price = exit_px
#             self.trade.exit.exit_reason = reason
#             self.trade.exit.exit_ratio = total_ratio
#             self.trade.pending_exit = None
#             return True
#         self.trade.lifecycle = Lifecycle.OPEN
#         self.trade.outcome.result = None
#         return False

#     def _holding_days(
#         self,
#         current_date: str,
#         rule: ExpirationRule,
#         *,
#         calendar: Optional[Any],
#     ) -> int:
#         entry_date = str(self.trade.entry.entry_date or "").strip()
#         cur = str(current_date or "").strip()
#         if not entry_date or not cur:
#             return 0

#         if rule.mode == ExpirationMode.NATURAL_DAY:
#             return self._natural_day_count(entry_date, cur)

#         if rule.mode == ExpirationMode.OPEN_DAY:
#             if calendar is None:
#                 return self._natural_day_count(entry_date, cur)
#             return int(calendar.count_open_days_between(entry_date, cur))

#         return self._trading_day_count(entry_date, cur, calendar=calendar)

#     def _natural_day_count(self, start_date: str, end_date: str) -> int:
#         start = str(start_date or "").strip()
#         end = str(end_date or "").strip()
#         if not start or not end:
#             return 0
#         try:
#             start_dt = datetime.strptime(start, "%Y%m%d")
#             end_dt = datetime.strptime(end, "%Y%m%d")
#             return max((end_dt - start_dt).days, 0)
#         except Exception:
#             return 0

#     def _trading_day_count(
#         self,
#         entry_date: str,
#         current_date: str,
#         *,
#         calendar: Optional[Any],
#     ) -> int:
#         """随模拟 K 线推进：仅在开市日累加（需交易日历）。"""
#         holding = self.trade.holding
#         if calendar is None:
#             return self._natural_day_count(entry_date, current_date)

#         if not holding.counter_initialized:
#             holding.last_bar_date = entry_date
#             holding.trading_day_count = int(calendar.count_open_days_between(entry_date, entry_date))
#             holding.counter_initialized = True

#         last = str(holding.last_bar_date or entry_date)
#         cur = str(current_date or "")
#         if cur > last:
#             if calendar.is_open_date(cur):
#                 holding.trading_day_count += 1
#             holding.last_bar_date = cur
#             return holding.trading_day_count
#         if cur < last:
#             return int(calendar.count_open_days_between(entry_date, cur))
#         return holding.trading_day_count

#     def _settle(
#         self,
#         exit_date: str,
#         exit_price: float,
#         exit_reason: str,
#         roi: float,
#         exit_ratio: float = 1.0,
#         *,
#         market_profile: Optional[Any] = None,
#         prev_bar: Optional[Dict[str, Any]] = None,
#         stock_status_risk: Optional[Any] = None,
#         exec_bar: Optional[Dict[str, Any]] = None,
#     ) -> None:
#         basis = self._cost_basis()
#         profit = self._directional_profit(exit_price, basis)
#         goal_entry = {
#             "opportunity_id": self.meta.opportunity_id,
#             "date": exit_date,
#             "direction": self.entry.direction.value,
#             "entry_price": basis,
#             "exit_price": exit_price,
#             "reason": exit_reason,
#             "roi": roi,
#             "exit_ratio": exit_ratio,
#             "profit": profit,
#             "weighted_profit": profit * exit_ratio,
#         }
#         if market_profile is not None:
#             self._stamp_goal_tradability(
#                 goal_entry,
#                 market_profile,
#                 prev_bar,
#                 exit_price,
#                 stock_status_risk=stock_status_risk,
#                 trade_date=exit_date,
#                 exec_bar=exec_bar,
#             )
#         self.trade.completed_goals.append(goal_entry)
#         total_weighted_profit = sum(
#             float(t.get("weighted_profit", 0) or 0) for t in self.trade.completed_goals
#         )
#         self.trade.outcome.price_return = roi
#         if self._apply_partial_or_complete(
#             total_weighted_profit, basis, exit_date, exit_price, exit_reason
#         ):
#             return
#         self.trade.exit.exit_date = exit_date
#         self.trade.exit.exit_price = exit_price
#         self.trade.exit.exit_reason = exit_reason

#     @classmethod
#     def from_opportunity(cls, opportunity: Opportunity, **kwargs: Any) -> "Investment":
#         investment_fields = {f.name for f in fields(cls)} - {f.name for f in fields(Opportunity)}
#         overrides = {key: value for key, value in kwargs.items() if key in investment_fields}
#         return cls(
#             stock=opportunity.stock,
#             record_of_today=dict(opportunity.record_of_today),
#             trigger_date=opportunity.trigger_date,
#             trigger_price=opportunity.trigger_price,
#             meta=OpportunityMeta(
#                 opportunity_id=opportunity.meta.opportunity_id,
#                 scan_date=opportunity.meta.scan_date,
#                 created_at=opportunity.meta.created_at,
#                 updated_at=opportunity.meta.updated_at,
#                 config_hash=opportunity.meta.config_hash,
#             ),
#             contributor=OpportunityContributor(
#                 strategy_name=opportunity.contributor.strategy_name,
#                 strategy_version=opportunity.contributor.strategy_version,
#             ),
#             extra_fields=dict(opportunity.extra_fields),
#             metadata=dict(opportunity.metadata),
#             **overrides,
#         )

#     @classmethod
#     def from_dict(cls, data: Dict[str, Any]) -> "Investment":
#         raw = dict(data or {})
#         opportunity = Opportunity.from_dict(raw)
#         investment_field_names = {f.name for f in fields(cls)} - {f.name for f in fields(Opportunity)}
#         overrides: Dict[str, Any] = {}
#         for key in investment_field_names:
#             if key not in raw:
#                 continue
#             value = raw[key]
#             if key == "trade" and isinstance(value, dict):
#                 overrides["trade"] = cls._parse_trade_state(value)
#             else:
#                 overrides[key] = value
#         return cls.from_opportunity(opportunity, **overrides)

#     @classmethod
#     def _parse_trade_state(cls, raw: Dict[str, Any]) -> TradeState:
#         lifecycle_raw = raw.get("lifecycle", Lifecycle.PENDING_TO_BUY.value)
#         lifecycle = lifecycle_raw if isinstance(lifecycle_raw, Lifecycle) else Lifecycle(str(lifecycle_raw))

#         entry_raw = raw.get("entry") if isinstance(raw.get("entry"), dict) else {}
#         direction_raw = entry_raw.get("direction", TradeSide.BUY.value)
#         direction = direction_raw if isinstance(direction_raw, TradeSide) else TradeSide(str(direction_raw))
#         entry = EntryInfo(
#             entry_price=float(entry_raw.get("entry_price") or 0.0),
#             entry_date=str(entry_raw.get("entry_date") or ""),
#             direction=direction,
#         )

#         exit_raw = raw.get("exit") if isinstance(raw.get("exit"), dict) else {}
#         exit_info = ExitInfo(
#             exit_price=cls._to_opt_float(exit_raw.get("exit_price")),
#             exit_date=str(exit_raw.get("exit_date") or ""),
#             exit_reason=str(exit_raw.get("exit_reason") or ""),
#             exit_ratio=float(exit_raw.get("exit_ratio") or 0.0),
#         )

#         pending_raw = raw.get("pending_exit")
#         pending_exit = None
#         if isinstance(pending_raw, dict):
#             pending_exit = PendingExit(
#                 reason=str(pending_raw.get("reason") or ""),
#                 exit_ratio=float(pending_raw.get("exit_ratio", pending_raw.get("sell_ratio", 1.0)) or 1.0),
#             )

#         holding_raw = raw.get("holding") if isinstance(raw.get("holding"), dict) else {}
#         mode_raw = holding_raw.get("mode")
#         mode = None
#         if mode_raw:
#             mode = mode_raw if isinstance(mode_raw, ExpirationMode) else ExpirationMode(str(mode_raw))
#         holding = HoldingState(
#             mode=mode,
#             window_days=int(holding_raw.get("window_days") or 0),
#             days=int(holding_raw.get("days") or 0),
#             last_bar_date=str(holding_raw.get("last_bar_date") or ""),
#             trading_day_count=int(holding_raw.get("trading_day_count") or 0),
#             counter_initialized=bool(holding_raw.get("counter_initialized", False)),
#         )

#         extreme_raw = raw.get("extreme") if isinstance(raw.get("extreme"), dict) else {}
#         extreme = ExtremePriceEdge(
#             highest=cls._to_opt_float(extreme_raw.get("highest")),
#             lowest=cls._to_opt_float(extreme_raw.get("lowest")),
#             highest_date=str(extreme_raw.get("highest_date") or ""),
#             lowest_date=str(extreme_raw.get("lowest_date") or ""),
#             highest_return=cls._to_opt_float(extreme_raw.get("highest_return", extreme_raw.get("highest_percentage"))),
#             lowest_return=cls._to_opt_float(extreme_raw.get("lowest_return", extreme_raw.get("lowest_percentage"))),
#         )

#         risk_raw = raw.get("risk") if isinstance(raw.get("risk"), dict) else {}
#         risk = RiskState(
#             protect_loss_active=bool(risk_raw.get("protect_loss_active", False)),
#             dynamic_loss_active=bool(risk_raw.get("dynamic_loss_active", False)),
#             dynamic_loss_peak=cls._to_opt_float(
#                 risk_raw.get("dynamic_loss_peak", risk_raw.get("dynamic_loss_highest"))
#             ),
#             triggered_stop_loss_idx=int(risk_raw.get("triggered_stop_loss_idx", -1)),
#             triggered_take_profit_idx=int(risk_raw.get("triggered_take_profit_idx", -1)),
#         )

#         outcome_raw = raw.get("outcome") if isinstance(raw.get("outcome"), dict) else {}
#         result_raw = outcome_raw.get("result")
#         result = None
#         if result_raw:
#             result = result_raw if isinstance(result_raw, InvestmentResult) else InvestmentResult(str(result_raw))
#         outcome = OutcomePerformance(
#             result=result,
#             weighted_roi=float(outcome_raw.get("weighted_roi", outcome_raw.get("roi", 0.0)) or 0.0),
#             price_return=cls._to_opt_float(outcome_raw.get("price_return")),
#             max_drawdown=cls._to_opt_float(outcome_raw.get("max_drawdown")),
#         )

#         return TradeState(
#             lifecycle=lifecycle,
#             entry=entry,
#             exit=exit_info,
#             pending_exit=pending_exit,
#             holding=holding,
#             extreme=extreme,
#             risk=risk,
#             outcome=outcome,
#             completed_goals=list(raw.get("completed_goals") or raw.get("completed_targets") or []),
#         )

#     @staticmethod
#     def _resolve_result(profit: float) -> InvestmentResult:
#         return InvestmentResult.WIN if profit > 0 else InvestmentResult.LOSS

#     @staticmethod
#     def _to_opt_float(value: Any) -> Optional[float]:
#         if value is None or value == "":
#             return None
#         if isinstance(value, (int, float)):
#             return float(value)
#         try:
#             return float(str(value).strip())
#         except (TypeError, ValueError):
#             return None

#     @staticmethod
#     def _bar_float(bar: Dict[str, Any], key: str) -> float:
#         try:
#             return float(bar.get(key) or 0.0)
#         except (TypeError, ValueError):
#             return 0.0

#     @classmethod
#     def _model_value(cls, model: Any) -> str:
#         if model is None:
#             return "close"
#         if hasattr(model, "value"):
#             return str(model.value).strip().lower()
#         return str(model).strip().lower()

#     @classmethod
#     def _monitor_bar_price(cls, kline: Dict[str, Any], model: Any) -> float:
#         key = cls._model_value(model)
#         if key == "extreme":
#             h = cls._bar_float(kline, "high")
#             l = cls._bar_float(kline, "low")
#             c = cls._bar_float(kline, "close")
#             return (h + l) / 2.0 if h and l else c
#         return cls._bar_float(kline, "close")

#     @classmethod
#     def _trade_price_defers_to_next_session(cls, model: Any) -> bool:
#         return cls._model_value(model) == "next_open"

#     @classmethod
#     def _trade_theoretical_price_on_bar(
#         cls,
#         model: Any,
#         *,
#         side: str,
#         bar: Dict[str, Any],
#     ) -> Optional[float]:
#         key = cls._model_value(model)
#         if key == "close":
#             return cls._bar_float(bar, "close")
#         if key in ("open", "next_open"):
#             return cls._bar_float(bar, "open") or cls._bar_float(bar, "close")
#         if side == TradeSide.BUY.value:
#             return cls._bar_float(bar, "high") or cls._bar_float(bar, "close")
#         return cls._bar_float(bar, "low") or cls._bar_float(bar, "close")

#     @staticmethod
#     def _parse_expiration_mode(exp: Dict[str, Any]) -> ExpirationMode:
#         raw_mode = exp.get("mode")
#         if raw_mode is not None and str(raw_mode).strip():
#             mode = str(raw_mode).strip().lower()
#             if mode in {m.value for m in ExpirationMode}:
#                 return ExpirationMode(mode)
#             raise ValueError(f"goal.expiration.mode 无效: {raw_mode!r}")

#         if "is_trading_days" in exp:
#             return ExpirationMode.OPEN_DAY if bool(exp.get("is_trading_days", True)) else ExpirationMode.NATURAL_DAY

#         return ExpirationMode.OPEN_DAY

#     @classmethod
#     def _parse_expiration_rules(cls, goal_config: Optional[Dict[str, Any]]) -> List[ExpirationRule]:
#         if not isinstance(goal_config, dict):
#             return []

#         rules: List[ExpirationRule] = []
#         exp = goal_config.get("expiration")
#         if isinstance(exp, dict):
#             try:
#                 window = int(exp.get("fixed_window_in_days") or exp.get("window_days") or 0)
#             except (TypeError, ValueError):
#                 window = 0
#             if window > 0:
#                 rules.append(
#                     ExpirationRule(
#                         window_days=window,
#                         mode=cls._parse_expiration_mode(exp),
#                     )
#                 )

#         # ``max_holding_days`` 已并入 ``goal.expiration``（如 ``mode=open_day``）。
#         return rules

#     @staticmethod
#     def _calendar_from_raw(raw: Any) -> Optional[Any]:
#         if raw is None:
#             return None
#         if hasattr(raw, "count_open_days_between") and hasattr(raw, "is_open_date"):
#             return raw
#         if not isinstance(raw, dict):
#             return None
#         dates = raw.get("open_dates")
#         if not isinstance(dates, list) or not dates:
#             return None
#         open_dates: Tuple[str, ...] = tuple(sorted({str(d).strip() for d in dates if str(d).strip()}))

#         class _Ctx:
#             def __init__(self, seq: Tuple[str, ...]) -> None:
#                 self._dates = seq

#             def is_open_date(self, trade_date: str) -> bool:
#                 return str(trade_date or "").strip() in self._dates

#             def count_open_days_between(self, start_date: str, end_date: str) -> int:
#                 start = str(start_date or "").strip()
#                 end = str(end_date or "").strip()
#                 if not start or not end:
#                     return 0
#                 if start > end:
#                     start, end = end, start
#                 return len([d for d in self._dates if start <= d <= end])

#         return _Ctx(open_dates)

#     @staticmethod
#     def _stamp_goal_tradability(
#         goal: Dict[str, Any],
#         market_profile: Any,
#         prev_bar: Optional[Dict[str, Any]],
#         exit_price: float,
#         *,
#         stock_status_risk: Optional[Any] = None,
#         trade_date: Optional[str] = None,
#         exec_bar: Optional[Dict[str, Any]] = None,
#     ) -> None:
#         """TODO: tradability helper (limit-down / bar volume on completed goal rows)."""
#         _ = (goal, market_profile, prev_bar, exit_price)
#         _ = stock_status_risk, trade_date, exec_bar

#     def _apply_stock_status_risk_management(
#         self,
#         sim: Any,
#         current_bar: Dict[str, Any],
#         stock_status_risk: Any,
#         *,
#         prev_bar: Optional[Dict[str, Any]] = None,
#         market_profile: Optional[Any] = None,
#     ) -> bool:
#         """TODO: goal.stock_status_risk_management + delist forced exit."""
#         _ = (sim, current_bar, stock_status_risk, prev_bar, market_profile)
#         return False

#     def _apply_stock_status_risk_management_from_settings(
#         self,
#         sim: Any,
#         current_bar: Dict[str, Any],
#         *,
#         prev_bar: Optional[Dict[str, Any]] = None,
#         market_profile: Optional[Any] = None,
#     ) -> bool:
#         """TODO: build stock_status_risk context from settings when absent."""
#         _ = (sim, current_bar, prev_bar, market_profile)
#         return False


# __all__ = [
#     "ExpirationMode",
#     "ExpirationRule",
#     "ExitInfo",
#     "ExitReason",
#     "ExtremePriceEdge",
#     "HoldingState",
#     "Investment",
#     "InvestmentResult",
#     "Lifecycle",
#     "OutcomePerformance",
#     "PendingExit",
#     "RiskState",
#     "TradeSide",
#     "TradeState",
#     "EntryInfo",
#     ]
