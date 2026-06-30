"""
Backtest engine module — unified timeline / sliced scheduling.

Public API:
- BacktestEngine — facade（``backtest_engine.py``）
- contracts — 执行契约（``contracts.py``）
"""

from core.modules.backtest_engine.backtest_engine import BacktestEngine

__all__ = ["BacktestEngine"]
