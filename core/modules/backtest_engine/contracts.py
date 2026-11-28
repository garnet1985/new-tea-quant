"""BacktestEngine 对外执行契约（跨模块 import 入口）。

引擎职责: job 调度 / 时间推进 / 性能监控。
slice_based 按片装数由调用方经 ``RunCallbacks.load_per_entity_window`` 注入。
"""
from core.modules.backtest_engine.core.performance.profiler import (
    ENGINE_PERF_KEY,
    ENUM_PERF_KEY,
    WorkerTaskPerf,
)
from core.modules.backtest_engine.core.shared.owned_shared_memory import (
    attach_shared_memory,
    close_and_unlink,
    create_owned_shared_memory,
)
from core.modules.backtest_engine.core.shared.progress import (
    RunPhase,
    attach_round,
    phase_probe_percent_range,
    phase_steps,
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
    JobReport,
    JobResult,
    JobStatus,
    LoadPerEntityWindowFn,
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
    "RunPhase",
    "attach_round",
    "attach_shared_memory",
    "close_and_unlink",
    "create_owned_shared_memory",
    "phase_probe_percent_range",
    "phase_steps",
    "JobContext",
    "JobFailure",
    "JobFailurePhase",
    "JobReport",
    "JobResult",
    "JobStatus",
    "LoadPerEntityWindowFn",
    "RunCallbacks",
    "RunProgress",
    "TaskStartFn",
    "TaskCompleteFn",
    "TickFn",
    "Timeline",
    "TimelineInput",
    "TimelineWorkerExecute",
    "WorkerTaskPerf",
]
