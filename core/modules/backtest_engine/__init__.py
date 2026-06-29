"""
Backtest engine module — unified timeline / sliced backtest scheduling.

Public API:
- BacktestEngine — sole facade entry (probe → plan → execute → report)
"""

from core.modules.backtest_engine.backtest_engine import BacktestEngine

__all__ = ["BacktestEngine"]
