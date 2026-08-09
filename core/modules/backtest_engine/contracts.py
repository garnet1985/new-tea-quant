"""BacktestEngine 对外执行契约（跨模块 import 入口）。

引擎职责: job 调度 / 时间推进 / 性能监控。
slice_based 探针/预读经 ``strategy.contracts.JobBundleLoader`` 装数（勿 deep-import strategy.core）。
"""
from core.modules.backtest_engine.core.performance.profiler import (
    ENGINE_PERF_KEY,
    ENUM_PERF_KEY,
    WorkerTaskPerf,
)
from core.modules.backtest_engine.core.schedule.entity_based.monitor import (
    EntityMonitorStats,
)
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
    "ENGINE_PERF_KEY",
    "ENUM_PERF_KEY",
    "EntityMonitorStats",
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
    "WorkerTaskPerf",
]
