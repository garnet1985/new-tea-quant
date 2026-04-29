#!/usr/bin/env python3
"""
Strategy 枚举定义
"""

from enum import Enum


class ExecutionMode(Enum):
    """执行模式"""

    SCAN = "scan"
    SIMULATE = "simulate"


class OpportunityStatus(Enum):
    """机会状态"""

    ACTIVE = "active"
    TESTING = "testing"
    CLOSED = "closed"
    EXPIRED = "expired"
    OPEN = "open"
    WIN = "win"
    LOSS = "loss"


class SellReason(Enum):
    """卖出原因"""

    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    MAX_HOLDING = "max_holding"
    END_OF_PERIOD = "end_of_period"


class ReuseAction(Enum):
    """Enumerator reuse action."""

    REUSE_FULL = "REUSE_FULL"
    RUN_DIFF_STOCKS = "RUN_DIFF_STOCKS"
    REBUILD_ALL = "REBUILD_ALL"


class NotReusedBecause(Enum):
    """Reason for not fully reusing previous enumerator results."""

    NONE = "NONE"
    NO_CACHE = "NO_CACHE"
    CACHE_MISS_OR_INVALIDATED = "CACHE_MISS_OR_INVALIDATED"
    CACHE_PARTIAL_STOCK_COVERAGE = "CACHE_PARTIAL_STOCK_COVERAGE"
    CACHE_COVERAGE_CONFLICT = "CACHE_COVERAGE_CONFLICT"
