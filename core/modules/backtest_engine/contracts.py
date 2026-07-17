"""BacktestEngine 对外执行契约（跨模块 import 入口）。"""
from core.modules.backtest_engine.core.shared.advancement import (
    AdvancementHooks,
    AdvancementHooksFactory,
    BoundAdvancementExecute,
    CalendarAdvancer,
    resolve_worker_execute_fn,
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
    JobReport,
    JobResult,
    JobStatus,
    RunCallbacks,
    RunProgress,
)

__all__ = [
    "AdvancementHooks",
    "AdvancementHooksFactory",
    "BoundAdvancementExecute",
    "BacktestJob",
    "BacktestMode",
    "CalendarAdvancer",
    "ExecuteFn",
    "TaskStartFn",
    "TaskCompleteFn",
    "JobContext",
    "JobFailure",
    "JobFailurePhase",
    "JobReport",
    "JobResult",
    "JobStatus",
    "RunCallbacks",
    "RunProgress",
    "resolve_worker_execute_fn",
]
