#!/usr/bin/env python3
"""Shared engine-level primitives and utilities."""

from .report_base import ReportBase
from .simulator_hooks_dispatcher import SimulatorHooksDispatcher
from .performance_profiler import PerformanceMetrics, PerformanceProfiler
from .data_classes import BaseInvestment, Opportunity

__all__ = [
    "ReportBase",
    "SimulatorHooksDispatcher",
    "PerformanceMetrics",
    "PerformanceProfiler",
    "BaseInvestment",
    "Opportunity",
]

