"""Investment — trading state and exit logic built on top of ``Opportunity``.

Naming:
- ``settings.goal`` / ``check_goals``: exit rules from strategy config.
- ``simulation.execute_steps``: ordered goal-check pipeline (see ``ExecuteStep``).
- ``completed_goals``: one row per partial or full exit leg.
- ``entry_*`` / ``exit_info.*`` / ``direction``: direction-neutral trade fields.
- ``outcome``: aggregated investment output; ``outcome.result`` is win/loss.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from core.modules.strategy.core.engines.shared.data_class.opportunity import (
    Opportunity,
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
    NATURAL_DAY = "natural_day"
    TRADING_DAY = "trading_day"
    OPEN_DAY = "open_day"


class ExecuteStep(str, Enum):
    """``simulation.execute_steps`` entries; each maps to an ``Investment`` handler."""

    CHECK_SETTLEMENT = "check_settlement"
    CHECK_STOP_LOSS = "check_stop_loss"
    CHECK_TAKE_PROFIT = "check_take_profit"
    CHECK_EXPIRATION = "check_expiration"

    @classmethod
    def parse(cls, value: Any) -> "ExecuteStep":
        text = str(value or "").strip().lower()
        if not text:
            raise ValueError("execute step must be a non-empty string")
        try:
            return cls(text)
        except ValueError as exc:
            allowed = ", ".join(step.value for step in cls)
            raise ValueError(f"unknown execute step {value!r}; allowed: {allowed}") from exc


DEFAULT_EXECUTE_STEPS: Tuple[ExecuteStep, ...] = (
    ExecuteStep.CHECK_SETTLEMENT,
    ExecuteStep.CHECK_STOP_LOSS,
    ExecuteStep.CHECK_TAKE_PROFIT,
    ExecuteStep.CHECK_EXPIRATION,
)

EXIT_TRIGGER_EXECUTE_STEPS: Tuple[ExecuteStep, ...] = (
    ExecuteStep.CHECK_STOP_LOSS,
    ExecuteStep.CHECK_TAKE_PROFIT,
    ExecuteStep.CHECK_EXPIRATION,
)


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
class Investment(Opportunity):
    """Extends ``Opportunity`` with grouped, direction-neutral trading state."""

    lifecycle: Lifecycle = Lifecycle.PENDING_TO_BUY
    entry: EntryInfo = field(default_factory=EntryInfo)
    exit_info: ExitInfo = field(default_factory=ExitInfo)
    pending_exit: Optional[PendingExit] = None
    holding: HoldingState = field(default_factory=HoldingState)
    extreme: ExtremePriceEdge = field(default_factory=ExtremePriceEdge)
    risk: RiskState = field(default_factory=RiskState)
    outcome: OutcomePerformance = field(default_factory=OutcomePerformance)
    completed_goals: List[Dict[str, Any]] = field(default_factory=list)
    execute_steps: List[ExecuteStep] = field(default_factory=list)

    _EXECUTE_STEP_HANDLERS: ClassVar[Dict[ExecuteStep, str]] = {
        ExecuteStep.CHECK_SETTLEMENT: "_check_settlement",
        ExecuteStep.CHECK_STOP_LOSS: "_check_stop_loss",
        ExecuteStep.CHECK_TAKE_PROFIT: "_check_take_profit",
        ExecuteStep.CHECK_EXPIRATION: "_check_expiration",
    }

    def resolve_execute_steps(self, settings: Optional[Dict[str, Any]] = None) -> List[ExecuteStep]:
        if self.execute_steps:
            return list(self.execute_steps)
        if settings is not None:
            from core.modules.strategy.core.engines.shared.services.strategy_settings.simulation_settings import (
                resolve_execute_steps,
            )

            return resolve_execute_steps(settings)
        return list(DEFAULT_EXECUTE_STEPS)

    def check_goals(self, *, settings: Optional[Dict[str, Any]] = None) -> bool:
        """Run ``simulation.execute_steps`` in order; True if an exit trigger fired."""
        for step in self.resolve_execute_steps(settings):
            if step == ExecuteStep.CHECK_SETTLEMENT:
                if not self._check_settlement():
                    return False
                continue
            handler_name = self._EXECUTE_STEP_HANDLERS[step]
            if getattr(self, handler_name)():
                return True
        return False

    def _check_settlement(self) -> bool:
        """Gate: False blocks remaining steps for this bar."""
        # TODO: market profile settlement + calendar
        return True

    def _check_stop_loss(self) -> bool:
        # TODO: stop loss, protect loss, dynamic loss
        return False

    def _check_take_profit(self) -> bool:
        # TODO: take profit stages
        return False

    def _check_expiration(self) -> bool:
        # TODO: goal.expiration (natural / trading / open day)
        return False

    def enter(self) -> bool:
        # TODO: entry fill + limit annotations
        return False

    def exit(self) -> bool:
        # TODO: execute exit leg
        return False

    def settle(self) -> bool:
        # TODO: force settle at simulate end
        return False


__all__ = [
    "DEFAULT_EXECUTE_STEPS",
    "EXIT_TRIGGER_EXECUTE_STEPS",
    "EntryInfo",
    "ExecuteStep",
    "ExitInfo",
    "ExitReason",
    "ExpirationMode",
    "ExpirationRule",
    "ExtremePriceEdge",
    "HoldingState",
    "Investment",
    "InvestmentResult",
    "Lifecycle",
    "OutcomePerformance",
    "PendingExit",
    "RiskState",
    "TradeSide",
]
