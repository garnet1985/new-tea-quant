"""BacktestEngine 对外执行契约（跨模块 import 入口）。

调用方请从此模块导入，勿使用 ``core.shared.types`` 等内部路径。
"""
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.backtest_engine.core.shared.types import (
    DispatchResult,
    ExecuteFn,
    ExecuteMode,
    ExecutionBackend,
    Job,
    JobContext,
    JobFailure,
    JobFailurePhase,
    JobReport,
    JobResult,
    JobStatus,
    RunProgress,
)

__all__ = [
    "BacktestJob",
    "DispatchResult",
    "ExecuteFn",
    "ExecuteMode",
    "ExecutionBackend",
    "Job",
    "JobContext",
    "JobFailure",
    "JobFailurePhase",
    "JobReport",
    "JobResult",
    "JobStatus",
    "RunProgress",
]
