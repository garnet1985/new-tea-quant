#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多进程执行器（Orchestrator 用 Executor 协议包装）。

旧 ProcessWorker pipeline 已移除；请使用 ``core.infra.job_dispatcher``。
"""

from typing import Any, Callable, Dict, List, Optional

from .base import Executor, JobResult
from ..multi_process.process_worker import (
    ExecutionMode,
    ProgressReportConfig,
)

_DEPRECATED_MSG = (
    "ProcessExecutor.run_jobs 已移除。请使用 JobDispatcher + create_job_executor(...)。"
)


class ProcessExecutor(Executor):
    """已废弃：请改用 JobDispatcher。"""

    def __init__(
        self,
        max_workers: Optional[int] = None,
        execution_mode: ExecutionMode = ExecutionMode.QUEUE,
        job_executor: Optional[Callable] = None,
        on_job_done: Optional[Callable[[Dict[str, Any]], None]] = None,
        progress_report_config: Optional[ProgressReportConfig] = None,
        is_main_process_used_if_single_worker: bool = True,
        is_verbose: bool = False,
    ) -> None:
        del (
            max_workers,
            execution_mode,
            job_executor,
            on_job_done,
            progress_report_config,
            is_main_process_used_if_single_worker,
            is_verbose,
        )

    def run_jobs(
        self,
        jobs: List[Dict[str, Any]],
        total_jobs: Optional[int] = None,
    ) -> List[JobResult]:
        del jobs, total_jobs
        raise RuntimeError(_DEPRECATED_MSG)

    def shutdown(self, timeout: float = 5.0) -> None:
        del timeout

    def get_stats(self) -> Dict[str, Any]:
        return {}
