#!/usr/bin/env python3
"""Shared investment base classes."""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from core.modules.strategy.engines.shared.data_classes.investment_state import (
    InvestmentLifecycle,
    InvestmentOutcome,
    InvestmentState,
    PendingExit,
    resolve_outcome,
)


@dataclass
class BaseInvestment(ABC):
    """投资基类（统一接口）"""

    investment_id: str
    opportunity_id: str
    stock_id: str
    buy_date: str
    buy_price: float
    stock_name: str = ""
    sell_date: Optional[str] = None
    sell_price: Optional[float] = None
    profit: float = 0.0
    roi: float = 0.0
    holding_days: int = 0
    lifecycle: str = InvestmentLifecycle.OPEN.value
    outcome: Optional[str] = None
    pending_exit: Optional[Dict[str, Any]] = None

    @property
    def investment_state(self) -> InvestmentState:
        pending = PendingExit.from_dict(self.pending_exit)
        out = None
        if self.outcome:
            try:
                out = InvestmentOutcome(str(self.outcome).strip().lower())
            except ValueError:
                out = None
        life = (
            InvestmentLifecycle.COMPLETE
            if str(self.lifecycle).strip().lower() == InvestmentLifecycle.COMPLETE.value
            else InvestmentLifecycle.OPEN
        )
        state = InvestmentState(lifecycle=life, outcome=out, pending_exit=pending)
        state.validate()
        return state

    def apply_investment_state(self, state: InvestmentState) -> None:
        state.validate()
        self.lifecycle = state.lifecycle.value
        self.outcome = state.outcome.value if state.outcome else None
        self.pending_exit = state.pending_exit.to_dict() if state.pending_exit else None

    def mark_complete(self, profit: float) -> None:
        self.apply_investment_state(InvestmentState().complete_with_profit(profit))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    @abstractmethod
    def from_source(cls, source: Any) -> "BaseInvestment":
        raise NotImplementedError


__all__ = ["BaseInvestment", "resolve_outcome"]
