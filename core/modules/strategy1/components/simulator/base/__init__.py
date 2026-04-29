#!/usr/bin/env python3
"""
Simulator base package

目前主要提供：
- SimulatorHooksDispatcher：用于在模拟器中调用用户在 StrategyWorker 中实现的钩子方法
- ReportBase：回测报告数据类基类
"""

from .report_base import ReportBase  # noqa: F401

__all__ = [
    "ReportBase",
]

