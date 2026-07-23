"""BacktestEngine 对外执行契约（跨模块 import 入口）。

引擎职责: job 调度 / 时间推进 / 性能监控。
数据装载（JobBundleLoader 等）由使用方经 on_before_task_start 注入，不在此导出。
"""
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.backtest_engine.core.shared.types import (
    ExecuteFn,
    JobContext,
    JobFailure,
    JobFailurePhase,
    TaskStartFn,
    TaskCompleteFn,
    TickFn,
    TicksCompleteFn,
    JobReport,
    JobResult,
    JobStatus,
    RunCallbacks,
    RunProgress,
)
from core.modules.backtest_engine.core.timeline import (
    Timeline,
    TimelineInput,
    TimelineWorkerExecute,
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
    "TaskStartFn",
    "TaskCompleteFn",
    "TickFn",
    "TicksCompleteFn",
    "Timeline",
    "TimelineInput",
    "TimelineWorkerExecute",
]
