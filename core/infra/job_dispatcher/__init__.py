"""
infra.job_dispatcher - 任务装填、分发与结果回收。
"""
from core.infra.job_dispatcher.executor import JobExecutor, create_job_executor
from core.infra.job_dispatcher.hooks import (
    ExecuteFn,
    OnReleaseHook,
    OnResultHook,
    ToExecutableJobHook,
)
from core.infra.job_dispatcher.job_dispatcher import JobDispatcher
from core.infra.job_dispatcher.probe import WorkerProbe
from core.infra.job_dispatcher.settings import JobDispatchSettings
from core.infra.job_dispatcher.types import (
    DataRef,
    DispatchResult,
    ExecuteMode,
    ExecutionBackend,
    Job,
    JobFailure,
    JobFailurePhase,
    JobReport,
    PreparedJob,
    RunProgress,
)

__all__ = [
    "DataRef",
    "DispatchResult",
    "ExecuteFn",
    "ExecuteMode",
    "ExecutionBackend",
    "Job",
    "JobDispatchSettings",
    "JobDispatcher",
    "JobExecutor",
    "JobFailure",
    "JobFailurePhase",
    "JobReport",
    "OnReleaseHook",
    "OnResultHook",
    "PreparedJob",
    "RunProgress",
    "ToExecutableJobHook",
    "WorkerProbe",
    "create_job_executor",
]
