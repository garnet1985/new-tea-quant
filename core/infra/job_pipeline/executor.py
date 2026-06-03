"""
JobExecutor - Dispatcher 使用的并发执行后端协议。
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from core.infra.job_pipeline.executors.pool import ProcessJobExecutor, ThreadJobExecutor
from core.infra.job_pipeline.hooks import ExecuteFn
from core.infra.job_pipeline.probe import WorkerProbe
from core.infra.job_pipeline.settings import JobPipelineSettings
from core.infra.job_pipeline.types import ExecutionBackend, JobContext


@runtime_checkable
class JobExecutor(Protocol):
    """流式 submit execute(JobContext) 的执行后端。"""

    @property
    def max_workers(self) -> int:
        ...

    @property
    def requires_picklable_payload(self) -> bool:
        ...

    def submit(self, context: JobContext) -> Any:
        ...

    def shutdown(self, *, wait: bool = True, timeout: float | None = None) -> None:
        ...

    def get_stats(self) -> dict[str, Any]:
        ...


def create_job_executor(settings: JobPipelineSettings, *, execute: ExecuteFn) -> JobExecutor:
    """由 JobPipelineSettings 构造 Process / Thread JobExecutor。"""
    resolved = WorkerProbe.resolve(
        settings.max_workers,
        reserve_cores=settings.reserve_cores,
        cap=settings.max_workers_cap,
    )
    if settings.worker == ExecutionBackend.PROCESS:
        return ProcessJobExecutor(
            max_workers=resolved,
            execute=execute,
            start_method=settings.start_method,
        )
    if settings.worker == ExecutionBackend.THREAD:
        return ThreadJobExecutor(max_workers=resolved, execute=execute)
    raise ValueError(f"Unsupported ExecutionBackend: {settings.worker!r}")
