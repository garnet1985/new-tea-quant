"""Investment 相关枚举（生命周期 / 成交 / 退出 / 结果 / 到期 / target check）。"""

from __future__ import annotations

from enum import Enum
from typing import Any, Tuple


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class Lifecycle(str, Enum):
    """Investment state machine."""

    OPEN = "open"
    PENDING_TO_ENTER = "pending_to_enter"  # 已建意图，进场条件未齐（如等次日 open）
    PENDING_TO_EXIT = "pending_to_exit"  # exit armed; awaiting fill / retry
    COMPLETE = "complete"  # archived; includes simulate-end force close


class PendingExitKind(str, Enum):
    """``PENDING_TO_EXIT`` 挂起原因（决定后续用什么价、何时可成交）。"""

    NEXT_OPEN_DEFER = "next_open_defer"  # 计划：次日 open 成交
    FILL_RETRY = "fill_retry"  # 失败重试：按原 exit_price 继续试


class ExitReason(str, Enum):
    EXPIRED = "expired"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    PROTECT_LOSS = "protect_loss"
    DYNAMIC_LOSS = "dynamic_loss"
    SIMULATE_END = "simulate_end"


class InvestmentResult(str, Enum):
    WIN = "win"
    LOSS = "loss"


class ExpirationMode(str, Enum):
    NATURAL_DAY = "natural_day"
    TRADING_DAY = "trading_day"
    OPEN_DAY = "open_day"


class TargetCheckStep(str, Enum):
    """``simulation.assumption.target_check_order`` — ``check_targets`` 内互斥目标顺序。

    同 bar 短路：先命中者武装出场。不含 settlement（门禁写死在 check_targets 前）。
    """

    CHECK_STOP_LOSS = "check_stop_loss"
    CHECK_TAKE_PROFIT = "check_take_profit"
    CHECK_EXPIRATION = "check_expiration"

    @classmethod
    def parse(cls, value: Any) -> "TargetCheckStep":
        text = str(value or "").strip().lower()
        if not text:
            raise ValueError("target check step must be a non-empty string")
        try:
            return cls(text)
        except ValueError as exc:
            allowed = ", ".join(step.value for step in cls)
            raise ValueError(
                f"unknown target check step {value!r}; allowed: {allowed}"
            ) from exc


DEFAULT_TARGET_CHECK_ORDER: Tuple[TargetCheckStep, ...] = (
    TargetCheckStep.CHECK_STOP_LOSS,
    TargetCheckStep.CHECK_TAKE_PROFIT,
    TargetCheckStep.CHECK_EXPIRATION,
)


__all__ = [
    "DEFAULT_TARGET_CHECK_ORDER",
    "ExitReason",
    "ExpirationMode",
    "InvestmentResult",
    "Lifecycle",
    "PendingExitKind",
    "TargetCheckStep",
    "TradeSide",
]
