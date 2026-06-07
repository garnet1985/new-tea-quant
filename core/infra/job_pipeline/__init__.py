"""
infra.job_pipeline - 并行 Job 执行管道（线程/进程池 + on_result）。

目录：
  types.py    — 公共类型
  pipeline/   — JobPipeline 编排（settings、hooks、runner）
  runtime/    — ProcessPool / ThreadPool 执行后端
  profile/    — worker.json 并行度与 dispatch 配置
"""
from core.infra.job_pipeline.pipeline import (
    ExecuteFn,
    JobPipeline,
    JobPipelineSettings,
    OnReleaseHook,
    OnResultHook,
)
from core.infra.job_pipeline.profile import WorkerProbe
from core.infra.job_pipeline.runtime import JobExecutor, create_job_executor
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
