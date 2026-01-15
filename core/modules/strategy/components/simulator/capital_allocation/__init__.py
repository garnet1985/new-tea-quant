#!/usr/bin/env python3
"""
Simulator.capital_allocation 子包

说明：
- 这是策略模块中资金分配模拟器的统一入口位置
- 当前实现文件已全部位于本子包下
"""

from .capital_allocation_simulator import CapitalAllocationSimulator  # noqa: F401
from .capital_allocation_simulator_config import CapitalAllocationSimulatorConfig  # noqa: F401

__all__ = [
    "CapitalAllocationSimulator",
    "CapitalAllocationSimulatorConfig",
]

