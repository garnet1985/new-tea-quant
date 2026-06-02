"""JobDispatcher 钩子协议。"""
from __future__ import annotations

from typing import Any, Callable, Optional, Protocol

from core.infra.job_dispatcher.types import Job, JobReport, PreparedJob, RunProgress


class ToExecutableJobHook(Protocol):
    """job → 装填后的 Job（主进程 IO）。"""

    def __call__(self, job: Job) -> Job:
        ...


class OnResultHook(Protocol):
    """处理 Worker 返回的报告（主进程 IO）。"""

    def __call__(self, report: JobReport, progress: RunProgress) -> None:
        ...


class OnReleaseHook(Protocol):
    """PreparedJob 生命周期结束（释放 spill / 内存）。"""

    def __call__(self, prepared: PreparedJob) -> None:
        ...


ExecuteFn = Callable[[dict[str, Any]], Any]
