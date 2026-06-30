"""
Backtest engine module — unified timeline / sliced scheduling.

Public API (target 0.3.0, see api.yaml):
- BacktestEngine — facade（entity_based / slice_based）
- contracts — BacktestJob, JobContext, RunCallbacks, …

用语：job dict {'id','payload'} ↔ BacktestJob；不用 wire。
"""

from core.modules.backtest_engine.backtest_engine import BacktestEngine

__all__ = ["BacktestEngine"]
