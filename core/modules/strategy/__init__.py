#!/usr/bin/env python3
"""
Strategy 模块：策略发现、扫描、simulate、枚举与双模拟器。

说明见模块 `README.md` 与 `docs/`；子组件见 `docs/components/`。
"""

from .strategy_manager import StrategyManager
from .base_strategy_worker import BaseStrategyWorker
from .models.opportunity import Opportunity
from .models.strategy_settings import StrategySettings
from .enums import ExecutionMode, OpportunityStatus, SellReason

__all__ = [
    'StrategyManager',
    'BaseStrategyWorker',
    'Opportunity',
    'StrategySettings',
    'ExecutionMode',
    'OpportunityStatus',
    'SellReason',
]
