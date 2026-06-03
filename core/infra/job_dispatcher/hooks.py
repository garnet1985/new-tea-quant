"""JobDispatcher 钩子协议。"""
from __future__ import annotations

from typing import Any, Callable, Protocol

from core.infra.job_dispatcher.types import JobContext, JobReport, RunProgress


class OnResultHook(Protocol):
    """处理 Worker 返回的报告（主进程）。"""

    def __call__(self, report: JobReport, progress: RunProgress) -> None:
        ...


class OnReleaseHook(Protocol):
    """单 job 执行结束后的可选清理（主进程，与 execute 配对）。"""

    def __call__(self, context: JobContext) -> None:
        ...


ExecuteFn = Callable[[JobContext], Any]
