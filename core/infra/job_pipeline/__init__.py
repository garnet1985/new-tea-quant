"""
infra.job_pipeline - 并行 Job 执行管道（线程/进程池 + on_result）。
"""
from core.infra.job_pipeline.executor import JobExecutor, create_job_executor
from core.infra.job_pipeline.hooks import ExecuteFn, OnReleaseHook, OnResultHook
from core.infra.job_pipeline.job_pipeline import JobPipeline
from core.infra.job_pipeline.probe import WorkerProbe
from core.infra.job_pipeline.settings import JobPipelineSettings
from core.infra.job_pipeline.types import (
    DispatchResult,
    ExecuteMode,
    ExecutionBackend,
    Job,
    JobContext,
    JobFailure,
    JobFailurePhase,
    JobReport,
    RunProgress,
)

__all__ = [
    "DispatchResult",
    "ExecuteFn",
    "ExecuteMode",
    "ExecutionBackend",
    "Job",
    "JobContext",
    "JobPipeline",
    "JobPipelineSettings",
    "JobExecutor",
    "JobFailure",
    "JobFailurePhase",
    "JobReport",
    "OnReleaseHook",
    "OnResultHook",
    "RunProgress",
    "WorkerProbe",
    "create_job_executor",
]
