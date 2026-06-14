#!/usr/bin/env python3
"""投资生命周期状态：open/complete 二元 + outcome + pending_exit 执行态。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Optional


class InvestmentLifecycle(str, Enum):
    OPEN = "open"
    COMPLETE = "complete"


class InvestmentOutcome(str, Enum):
    WIN = "win"
    LOSS = "loss"
    FLAT = "flat"


class ScanSignalPhase(str, Enum):
    """信号/建仓队列阶段（非投资生命周期）。"""

    ACTIVE = "active"
    TESTING = "testing"


@dataclass
class PendingExit:
    reason: str
    sell_ratio: float = 1.0
    triggered_date: str = ""
    deferred_from_date: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Any) -> Optional["PendingExit"]:
        if not isinstance(raw, dict) or not raw:
            return None
        try:
            ratio = float(raw.get("sell_ratio") or 1.0)
        except (TypeError, ValueError):
            ratio = 1.0
        return cls(
            reason=str(raw.get("reason") or "").strip(),
            sell_ratio=ratio,
            triggered_date=str(raw.get("triggered_date") or raw.get("date") or "").strip(),
            deferred_from_date=str(raw.get("deferred_from_date") or "").strip(),
        )


@dataclass
class InvestmentState:
    lifecycle: InvestmentLifecycle = InvestmentLifecycle.OPEN
    outcome: Optional[InvestmentOutcome] = None
    pending_exit: Optional[PendingExit] = None

    def validate(self) -> None:
        if self.lifecycle == InvestmentLifecycle.COMPLETE:
            if self.outcome is None:
                raise ValueError("complete 投资必须带 outcome")
            if self.pending_exit is not None:
                raise ValueError("complete 投资不得保留 pending_exit")
        if self.lifecycle == InvestmentLifecycle.OPEN and self.outcome is not None:
            raise ValueError("open 投资不得带 outcome")

    @property
    def is_open(self) -> bool:
        return self.lifecycle == InvestmentLifecycle.OPEN

    @property
    def is_complete(self) -> bool:
        return self.lifecycle == InvestmentLifecycle.COMPLETE

    def mark_pending_exit(self, pending: PendingExit) -> "InvestmentState":
        if self.lifecycle != InvestmentLifecycle.OPEN:
            raise ValueError("仅 open 投资可设置 pending_exit")
        return InvestmentState(
            lifecycle=InvestmentLifecycle.OPEN,
            outcome=None,
            pending_exit=pending,
        )

    def complete_with_profit(self, profit: float) -> "InvestmentState":
        return InvestmentState(
            lifecycle=InvestmentLifecycle.COMPLETE,
            outcome=resolve_outcome(profit),
            pending_exit=None,
        )

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"lifecycle": self.lifecycle.value}
        if self.outcome is not None:
            out["outcome"] = self.outcome.value
        if self.pending_exit is not None:
            out["pending_exit"] = self.pending_exit.to_dict()
        return out

    @classmethod
    def from_dict(cls, raw: Any) -> "InvestmentState":
        if not isinstance(raw, dict):
            return cls()
        life_raw = str(raw.get("lifecycle") or InvestmentLifecycle.OPEN.value).strip().lower()
        lifecycle = (
            InvestmentLifecycle.COMPLETE
            if life_raw == InvestmentLifecycle.COMPLETE.value
            else InvestmentLifecycle.OPEN
        )
        outcome = None
        out_raw = str(raw.get("outcome") or "").strip().lower()
        if out_raw in {o.value for o in InvestmentOutcome}:
            outcome = InvestmentOutcome(out_raw)
        pending = PendingExit.from_dict(raw.get("pending_exit"))
        state = cls(lifecycle=lifecycle, outcome=outcome, pending_exit=pending)
        state.validate()
        return state


def resolve_outcome(profit: float, *, eps: float = 1e-12) -> InvestmentOutcome:
    if profit > eps:
        return InvestmentOutcome.WIN
    if profit < -eps:
        return InvestmentOutcome.LOSS
    return InvestmentOutcome.FLAT


__all__ = [
    "InvestmentLifecycle",
    "InvestmentOutcome",
    "InvestmentState",
    "PendingExit",
    "ScanSignalPhase",
    "resolve_outcome",
]