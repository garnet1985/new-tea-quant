#!/usr/bin/env python3
"""
PriceFactorSimulator 组件入口

基于枚举器 SOT 结果的、仅关注价格路径的单股价格因子模拟器。

当前模块主要提供：
- PriceFactorSimulator: 主入口类，负责组织 SOT 版本解析、任务调度和结果汇总
- PriceFactorSimulatorWorker: 子进程 Worker，用于单股级别的机会回放与统计（后续逐步完善）
"""

from .price_factor_simulator import PriceFactorSimulator, PriceFactorSimulatorWorker

__all__ = [
    "PriceFactorSimulator",
    "PriceFactorSimulatorWorker",
]

