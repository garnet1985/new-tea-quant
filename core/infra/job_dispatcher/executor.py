"""
JobExecutor - Dispatcher 使用的并发执行后端协议。

多进程 / 多线程由 executors/pool 实现；JobDispatcher 只依赖本协议。
并行度（max_workers）与 execute 仅在 create_job_executor 配置。
"""
from __future__ import annotations

from typing import Any, Protocol, Union, runtime_checkable

from core.infra.job_dispatcher.executors.pool import ProcessJobExecutor, ThreadJobExecutor
from core.infra.job_dispatcher.hooks import ExecuteFn
from core.infra.job_dispatcher.resolve import resolve_max_workers
from core.infra.job_dispatcher.types import ExecutionBackend


@runtime_checkable
class JobExecutor(Protocol):
    """流式 submit execute(payload) 的执行后端。"""

    @property
    def max_workers(self) -> int:
        ...

    @property
    def requires_picklable_payload(self) -> bool:
        ...

    def submit(self, job_id: str, payload: dict[str, Any]) -> Any:
        ...

    def shutdown(self, *, wait: bool = True, timeout: float | None = None) -> None:
        ...

    def get_stats(self) -> dict[str, Any]:
        ...


def create_job_executor(
    backend: ExecutionBackend,
    *,
    max_workers: Union[str, int] = 1,
    execute: ExecuteFn,
    module_name: str = "default",
    start_method: str = "spawn",
) -> JobExecutor:
    """构造 Process / Thread JobExecutor。"""
    resolved = resolve_max_workers(max_workers, module_name)
    if backend == ExecutionBackend.PROCESS:
        return ProcessJobExecutor(
            max_workers=resolved,
            execute=execute,
            start_method=start_method,
        )
    if backend == ExecutionBackend.THREAD:
        return ThreadJobExecutor(max_workers=resolved, execute=execute)
    raise ValueError(f"Unsupported ExecutionBackend: {backend!r}")
