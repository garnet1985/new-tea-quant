"""Shared strategy data classes (opportunity, investment, calendar as-of).

消费者: scanner, enumerator, price_factor, portfolio
其它: contracts, hooks

``SimulateSession`` 在 ``simulate_session`` 子模块；勿在此 re-export，
以免 ``contracts`` → ``data_class`` → ``simulate_session`` → ``contracts`` 环依赖。
"""

from .calendar_as_of import CalendarAsOfContext, CalendarAsOfResult
from .investment import Investment
from .investments import (
    DEFAULT_TARGET_CHECK_ORDER,
    InvestmentResult,
    Lifecycle,
    PendingExitKind,
    TargetCheckStep,
    TradeSide,
)
from .opportunity import Opportunity, OpportunityContributor, OpportunityMeta, StockInfo

__all__ = [
    "CalendarAsOfContext",
    "CalendarAsOfResult",
    "DEFAULT_TARGET_CHECK_ORDER",
    "Investment",
    "InvestmentResult",
    "Lifecycle",
    "Opportunity",
    "OpportunityContributor",
    "OpportunityMeta",
    "PendingExitKind",
    "StockInfo",
    "TargetCheckStep",
    "TradeSide",
]
