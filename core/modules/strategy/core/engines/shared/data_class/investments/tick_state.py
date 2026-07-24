"""Investment 跨 tick 的 runtime 状态。

用通用 ``StateBag`` 承载 entry / exit / holding / extreme / outcome，
避免为每段再拆一套固定 dataclass；``PendingExit`` 仍单独建模（挂起成交协议）。
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .enums import Lifecycle, TradeSide


class StateBag:
    """通用可变字段袋（attribute ↔ dict）。

    缺省字段读为 ``None``；写入即登记。用于 lifecycle 各段观测/累加数据。
    """

    __slots__ = ("_data",)

    def __init__(self, **kwargs: Any) -> None:
        object.__setattr__(self, "_data", dict(kwargs))

    def __getattr__(self, name: str) -> Any:
        if name == "_data":
            raise AttributeError(name)
        return self._data.get(name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_data":
            object.__setattr__(self, name, value)
            return
        self._data[name] = value

    def __copy__(self) -> "StateBag":
        return StateBag(**self._data)

    def __deepcopy__(self, memo: Dict[int, Any]) -> "StateBag":
        return StateBag(**copy.deepcopy(self._data, memo))

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    @classmethod
    def from_mapping(cls, raw: Optional[Dict[str, Any]]) -> "StateBag":
        return cls(**dict(raw or {}))


def _default_entry() -> StateBag:
    return StateBag(
        entry_price=0.0,
        entry_price_raw=0.0,
        entry_date="",
        direction=TradeSide.BUY,
        buy_prev_close=None,
        buy_at_limit_up=None,
        buy_bar_volume=None,
    )


def _default_exit() -> StateBag:
    return StateBag(
        exit_price=None,
        exit_price_raw=None,
        exit_date="",
        exit_reason="",
        exit_ratio=0.0,
        sell_prev_close=None,
        sell_at_limit_down=None,
        sell_bar_volume=None,
    )


def _default_holding() -> StateBag:
    return StateBag(
        mode=None,
        window_days=0,
        days=0,
        last_bar_date="",
        trading_day_count=0,
        counter_initialized=False,
    )


def _default_extreme() -> StateBag:
    return StateBag(
        highest=None,
        lowest=None,
        highest_date="",
        lowest_date="",
        highest_return=None,
        lowest_return=None,
    )


def _default_outcome() -> StateBag:
    return StateBag(
        result=None,
        weighted_roi=0.0,
        price_return=None,
        max_drawdown=None,
    )


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
class InvestmentTickState:
    """Per-investment accumulators updated across react calls."""

    state: Lifecycle = Lifecycle.PENDING_TO_ENTER
    entry: StateBag = field(default_factory=_default_entry)
    exit_info: StateBag = field(default_factory=_default_exit)
    pending_exit: Optional[PendingExit] = None
    holding: StateBag = field(default_factory=_default_holding)
    extreme: StateBag = field(default_factory=_default_extreme)
    outcome: StateBag = field(default_factory=_default_outcome)
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

    def bags_to_dict(self) -> Dict[str, Any]:
        """导出各 StateBag / PendingExit（供 Investment.to_dict）。"""
        from dataclasses import asdict

        payload: Dict[str, Any] = {
            "entry": self.entry.to_dict(),
            "exit_info": self.exit_info.to_dict(),
            "holding": self.holding.to_dict(),
            "extreme": self.extreme.to_dict(),
            "outcome": self.outcome.to_dict(),
        }
        if self.pending_exit is not None:
            payload["pending_exit"] = asdict(self.pending_exit)
        return payload


__all__ = [
    "InvestmentTickState",
    "PendingExit",
    "StateBag",
]
