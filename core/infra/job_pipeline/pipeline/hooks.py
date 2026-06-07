"""JobPipeline 钩子协议。"""
from __future__ import annotations

from typing import Any, Callable, Protocol

from core.infra.job_pipeline.types import JobContext, JobReport, RunProgress


class OnResultHook(Protocol):
    def __call__(self, report: JobReport, progress: RunProgress) -> None:
        ...


class OnReleaseHook(Protocol):
    def __call__(self, context: JobContext) -> None:
        ...


ExecuteFn = Callable[[JobContext], Any]
