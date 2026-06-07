"""JobExecutor 协议与工厂。"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from core.infra.job_pipeline.pipeline.hooks import ExecuteFn
from core.infra.job_pipeline.pipeline.settings import JobPipelineSettings
from core.infra.job_pipeline.profile.resolver import resolve_pipeline_workers
from core.infra.job_pipeline.runtime.pool import ProcessJobExecutor, ThreadJobExecutor
from core.infra.job_pipeline.types import ExecutionBackend, JobContext


@runtime_checkable
class JobExecutor(Protocol):
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
    if settings.max_workers in (None, "", "auto"):
        resolved = resolve_pipeline_workers(worker_id=settings.worker_profile)
    else:
        resolved = max(1, int(settings.max_workers))
    if settings.worker == ExecutionBackend.PROCESS:
        return ProcessJobExecutor(
            max_workers=resolved,
            execute=execute,
            start_method=settings.start_method,
        )
    if settings.worker == ExecutionBackend.THREAD:
        return ThreadJobExecutor(max_workers=resolved, execute=execute)
    raise ValueError(f"Unsupported ExecutionBackend: {settings.worker!r}")
