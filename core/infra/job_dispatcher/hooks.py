"""
JobDispatcher 钩子协议。

主进程：on_stage_job、on_report
子进程：execute（由 infra.worker 执行）
"""
from __future__ import annotations

from typing import Any, Callable, Protocol

from core.infra.job_dispatcher.types import JobReport, JobShell, StagedJob


class OnStageJobHook(Protocol):
    """shell → StagedJob（主进程 IO：load / spill）。"""

    def __call__(self, shell: JobShell) -> StagedJob:
        ...


class OnReportHook(Protocol):
    """处理 Worker 返回的报告（主进程 IO：批量写库等）。"""

    def __call__(self, report: JobReport) -> None:
        ...


class OnReleaseStagedHook(Protocol):
    """StagedJob 生命周期结束（释放 spill / 内存）。"""

    def __call__(self, staged: StagedJob) -> None:
        ...


# Worker 侧纯计算；参数为 StagedJob.payload
ExecuteFn = Callable[[dict[str, Any]], Any]
