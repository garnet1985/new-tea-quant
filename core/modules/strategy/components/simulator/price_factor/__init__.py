#!/usr/bin/env python3
"""
Simulator.price_factor 子包

说明：
- 这是策略模块中价格因子模拟器的统一入口位置
- 当前实现文件已全部位于本子包下
"""

from .price_factor_simulator import PriceFactorSimulator, PriceFactorSimulatorWorker  # noqa: F401

__all__ = [
    "PriceFactorSimulator",
    "PriceFactorSimulatorWorker",
]

