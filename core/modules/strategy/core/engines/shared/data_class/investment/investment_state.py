"""Investment 跨 tick 的 runtime 状态（纯数据）。

进/出场成交共用 ``FillState``；其余段各自建模。
命名统一 enter / exit（不用 buy / sell），便于以后做空。
序列化由 ``Investment.to_dict`` 负责。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .enums import ExpirationMode, InvestmentResult, Lifecycle, TradeSide


@dataclass
class FillState:
    """进场/出场成交共用字段。"""

    price: float = 0.0
    price_raw: float = 0.0
    date: str = ""
    prev_close: Optional[float] = None
    at_limit: Optional[bool] = None
    bar_volume: Optional[float] = None


@dataclass
class EnterState(FillState):
    direction: TradeSide = TradeSide.BUY


@dataclass
class ExitState(FillState):
    reason: str = ""
    ratio: float = 0.0


@dataclass
class HoldingState:
    mode: Optional[ExpirationMode] = None
    window_days: int = 0
    days: int = 0
    last_bar_date: str = ""
    trading_day_count: int = 0
    counter_initialized: bool = False


@dataclass
class ExtremeState:
    highest: Optional[float] = None
    lowest: Optional[float] = None
    highest_date: str = ""
    lowest_date: str = ""
    highest_return: Optional[float] = None
    lowest_return: Optional[float] = None


@dataclass
class OutcomeState:
    result: Optional[InvestmentResult] = None
    weighted_roi: float = 0.0
    price_return: Optional[float] = None
    max_drawdown: Optional[float] = None


@dataclass
class PendingExit:
    """挂起出场（次日 open / 重试等）；与普通 exit 快照形状不同。"""

    reason: str = ""
    exit_ratio: float = 1.0
    goal_name: str = ""
    fill_bar: Optional[Dict[str, Any]] = None
    kind: str = ""
    armed_as_of: str = ""


@dataclass
class InvestmentState:
    """Per-investment accumulators updated across react calls."""

    state: Lifecycle = Lifecycle.PENDING_TO_ENTER
    entry: EnterState = field(default_factory=EnterState)
    exit_info: ExitState = field(default_factory=ExitState)
    pending_exit: Optional[PendingExit] = None
    holding: HoldingState = field(default_factory=HoldingState)
    extreme: ExtremeState = field(default_factory=ExtremeState)
    outcome: OutcomeState = field(default_factory=OutcomeState)
    completed_goals: List[Dict[str, Any]] = field(default_factory=list)
    customized_state: Dict[str, Any] = field(default_factory=dict)
    triggered_force_exit_tags: List[str] = field(default_factory=list)
    last_bar: Optional[Dict[str, Any]] = None
    triggered_stop_loss_idx: int = -1
    triggered_take_profit_idx: int = -1
    remaining_ratio: float = 1.0
    protect_loss_active: bool = False
    dynamic_loss_active: bool = False
    dynamic_loss_peak: Optional[float] = None


__all__ = [
    "FillState",
    "EnterState",
    "ExitState",
    "HoldingState",
    "ExtremeState",
    "OutcomeState",
    "PendingExit",
    "InvestmentState",
]
