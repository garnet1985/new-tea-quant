#!/usr/bin/env python3
"""
Capital Allocation Simulator

资金分配型模拟器，在真实资金约束下对枚举器 SOT 结果进行全市场回放。
"""

from .capital_allocation_simulator_config import CapitalAllocationSimulatorConfig
from .version_manager import CapitalAllocationSimulationVersionManager
from .capital_allocation_simulator import CapitalAllocationSimulator

__all__ = [
    "CapitalAllocationSimulatorConfig",
    "CapitalAllocationSimulationVersionManager",
    "CapitalAllocationSimulator",
]
