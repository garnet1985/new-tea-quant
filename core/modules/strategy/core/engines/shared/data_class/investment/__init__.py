"""Investment 相关小类型整块。

消费者: scanner, enumerator, price_factor
其它: contracts, tests

- enums / investment_state：data
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
from .investment_state import (
    EnterState,
    ExitState,
    ExtremeState,
    FillState,
    HoldingState,
    InvestmentState,
    OutcomeState,
    PendingExit,
)

__all__ = [
    "DEFAULT_TARGET_CHECK_ORDER",
    "EnterState",
    "ExitReason",
    "ExitState",
    "ExpirationMode",
    "ExtremeState",
    "FillState",
    "HoldingState",
    "InvestmentResult",
    "InvestmentState",
    "Lifecycle",
    "OutcomeState",
    "PendingExit",
    "PendingExitKind",
    "TargetCheckStep",
    "TradeSide",
]
