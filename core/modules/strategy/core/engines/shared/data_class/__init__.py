"""Shared strategy data classes (opportunity, investment)."""

from .investment import (
    DEFAULT_EXECUTE_STEPS,
    ExecuteStep,
    Investment,
    InvestmentRunDeps,
    InvestmentTickInput,
    InvestmentResult,
    Lifecycle,
    PendingExitKind,
    TradeSide,
)
from .opportunity import Opportunity, OpportunityContributor, OpportunityMeta, StockInfo

__all__ = [
    "DEFAULT_EXECUTE_STEPS",
    "ExecuteStep",
    "Investment",
    "InvestmentRunDeps",
    "InvestmentTickInput",
    "InvestmentResult",
    "Lifecycle",
    "Opportunity",
    "OpportunityContributor",
    "OpportunityMeta",
    "PendingExitKind",
    "StockInfo",
    "TradeSide",
]
