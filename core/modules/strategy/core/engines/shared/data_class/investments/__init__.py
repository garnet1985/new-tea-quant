"""Investment 相关小类型整块。

消费者: scanner, enumerator, price_factor
其它: contracts, tests

- enums / run_deps / tick_state：data
- K 线安全取值：见 ``shared.services.safe_values.safe_bar_value.SafeBarValue``
"""

from .enums import (
    DEFAULT_EXECUTE_STEPS,
    EXIT_TRIGGER_EXECUTE_STEPS,
    ExecuteStep,
    ExitReason,
    ExpirationMode,
    InvestmentResult,
    Lifecycle,
    PendingExitKind,
    TradeSide,
)
from .run_deps import InvestmentRunDeps
from .tick_state import InvestmentTickState, PendingExit, StateBag

__all__ = [
    "DEFAULT_EXECUTE_STEPS",
    "EXIT_TRIGGER_EXECUTE_STEPS",
    "ExecuteStep",
    "ExitReason",
    "ExpirationMode",
    "InvestmentResult",
    "InvestmentRunDeps",
    "InvestmentTickState",
    "Lifecycle",
    "PendingExit",
    "PendingExitKind",
    "StateBag",
    "TradeSide",
]
