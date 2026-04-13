#!/usr/bin/env python3
"""
兼容旧 import 名：实现已迁至 ``data_management.strategy_data_manager.StrategyDataManager``。
"""

from core.modules.strategy.components.data_management.strategy_data_manager import (
    StrategyDataManager,
)


class StrategyWorkerDataManager(StrategyDataManager):
    """保留类名；新代码请直接使用 ``StrategyDataManager``。"""
