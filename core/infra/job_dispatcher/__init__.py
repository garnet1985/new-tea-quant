"""
infra.job_dispatcher - 任务装填、分发与结果回收（与 infra.worker 平级组合）。
"""
from core.infra.job_dispatcher.executor import JobExecutor, create_job_executor
from core.infra.job_dispatcher.hooks import (
    ExecuteFn,
    OnReleaseStagedHook,
    OnReportHook,
    OnStageJobHook,
)
from core.infra.job_dispatcher.job_dispatcher import JobDispatcher
from core.infra.job_dispatcher.types import (
    DataRef,
    DispatchConfig,
    DispatchResult,
    ExecutionBackend,
    FillStrategy,
    JobFailure,
    JobFailurePhase,
    JobReport,
    JobShell,
    StagedJob,
)

__all__ = [
    "DataRef",
    "DispatchConfig",
    "DispatchResult",
    "ExecuteFn",
    "ExecutionBackend",
    "FillStrategy",
    "JobDispatcher",
    "JobExecutor",
    "create_job_executor",
    "JobFailure",
    "JobFailurePhase",
    "JobReport",
    "JobShell",
    "OnReleaseStagedHook",
    "OnReportHook",
    "OnStageJobHook",
    "StagedJob",
]
