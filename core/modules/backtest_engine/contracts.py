"""BacktestEngine 对外执行契约（跨模块 import 入口）。"""
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.backtest_engine.core.shared.types import (
    ExecuteFn,
    JobContext,
    JobFailure,
    JobFailurePhase,
    JobReport,
    JobResult,
    JobStatus,
    RunCallbacks,
    RunProgress,
)

__all__ = [
    "BacktestJob",
    "BacktestMode",
    "ExecuteFn",
    "JobContext",
    "JobFailure",
    "JobFailurePhase",
    "JobReport",
    "JobResult",
    "JobStatus",
    "RunCallbacks",
    "RunProgress",
]
