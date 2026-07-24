"""Investment 相关小类型整块。

消费者: scanner, enumerator, price_factor
其它: contracts, tests

- enums / tick_state：data
- K 线安全取值：见 ``shared.services.safe_values.safe_bar_value.SafeBarValue``
"""

from .enums import (
    DEFAULT_TARGET_CHECK_ORDER,
    ExitReason,
    ExpirationMode,
    InvestmentResult,
    Lifecycle,
    PendingExitKind,
    TargetCheckStep,
    TradeSide,
)
from .tick_state import InvestmentTickState, PendingExit, StateBag

__all__ = [
    "DEFAULT_TARGET_CHECK_ORDER",
    "ExitReason",
    "ExpirationMode",
    "InvestmentResult",
    "InvestmentTickState",
    "Lifecycle",
    "PendingExit",
    "PendingExitKind",
    "StateBag",
    "TargetCheckStep",
    "TradeSide",
]
