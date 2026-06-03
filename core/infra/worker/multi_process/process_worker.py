#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多进程 Worker（已废弃）。

队列填池、BATCH/QUEUE pipeline 已移除，请使用 ``core.infra.job_dispatcher``：

    JobDispatcher(execute=..., on_result=..., executor=create_job_executor(...)).run(jobs)

本模块保留 ``JobStatus`` / ``JobResult`` 与 ``resolve_max_workers`` 等工具符号，供迁移期引用。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

_DEPRECATED_RUN_MSG = (
    "ProcessWorker.run_jobs 已移除。请使用 core.infra.job_dispatcher.JobDispatcher："
    "execute(JobContext) / on_result + create_job_executor(...)。"
    "队列填池与 auto max_workers 已上移至 JobDispatcher。"
)


class ExecutionMode(Enum):
    """已废弃：旧 BATCH / QUEUE 模式枚举，仅保留导入兼容。"""

    BATCH = "batch"
    QUEUE = "queue"


class JobStatus(Enum):
    """任务状态（worker 模块结果类型，与 JobDispatcher 无直接耦合）。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobResult:
    """任务执行结果。"""

    job_id: str
    status: JobStatus
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0

    def __str__(self) -> str:
        return (
            f"JobResult(job_id={self.job_id}, status={self.status.value}, "
            f"duration={self.duration:.2f}s)"
        )


class ProgressReportMode(Enum):
    """已废弃：旧进度日志模式，仅保留导入兼容。"""

    NONE = "none"
    EVERY_JOB_DONE = "every_job_done"
    EVERY_SEC_INTERVAL = "every_sec_interval"
    EVERY_PROGRESS_INTERVAL = "every_progress_interval"


@dataclass
class ProgressReportConfig:
    """已废弃：旧进度日志配置，仅保留导入兼容。"""

    mode: ProgressReportMode = ProgressReportMode.EVERY_PROGRESS_INTERVAL
    interval_seconds: float = 2.0
    interval_pct: int = 5
    log_on_run_started: bool = False
    log_on_run_finished: bool = True


class ProcessWorker:
    """
    已废弃的多进程任务执行器壳。

    新代码请组合 ``JobDispatcher`` + ``create_job_executor``。
    """

    @staticmethod
    def calculate_workers(task_type, reserve_cores: int = 2) -> int:
        """已废弃：请使用 ``WorkerProbe.resolve``。"""
        import multiprocessing as mp

        from core.infra.worker.multi_process.task_type import TaskType

        cpu_count = mp.cpu_count() or 1
        if task_type == TaskType.CPU_INTENSIVE:
            physical_cores = max(1, cpu_count // 2)
            return max(1, physical_cores - reserve_cores)
        if task_type == TaskType.IO_INTENSIVE:
            return max(2, cpu_count - reserve_cores + 1)
        return max(1, cpu_count - reserve_cores)

    @staticmethod
    def resolve_max_workers(max_workers, module_name: str = "default") -> int:
        del module_name  # 已废弃；并行度由 WorkerProbe 解析
        from core.infra.job_dispatcher.probe import WorkerProbe

        return WorkerProbe.resolve(max_workers)

    def __init__(
        self,
        max_workers: Optional[int] = None,
        execution_mode: ExecutionMode = ExecutionMode.QUEUE,
        batch_size: Optional[int] = None,
        job_executor: Optional[Callable] = None,
        on_job_done: Optional[Callable[[Dict[str, Any]], None]] = None,
        progress_report_config: Optional[ProgressReportConfig] = None,
        is_main_process_used_if_single_worker: bool = True,
        enable_monitoring: bool = True,
        timeout: float = 300.0,
        is_verbose: bool = False,
        debug: bool = False,
        start_method: str = "spawn",
    ) -> None:
        del (
            batch_size,
            on_job_done,
            progress_report_config,
            is_main_process_used_if_single_worker,
            enable_monitoring,
            timeout,
            debug,
            start_method,
        )
        self.max_workers = max_workers
        self.execution_mode = execution_mode
        self.job_executor = job_executor
        self.is_verbose = is_verbose
        self.stats: Dict[str, Any] = {}
        self.results: List[JobResult] = []

    def _deprecated(self) -> None:
        raise RuntimeError(_DEPRECATED_RUN_MSG)

    def set_job_executor(self, job_executor: Callable) -> None:
        self.job_executor = job_executor

    def add_job(self, job_id: str, job_payload: Any) -> None:
        del job_id, job_payload
        self._deprecated()

    def add_jobs(self, jobs: List[Dict[str, Any]]) -> None:
        del jobs
        self._deprecated()

    def run_jobs(
        self,
        jobs: Optional[List[Dict[str, Any]]] = None,
        total_jobs: Optional[int] = None,
    ) -> Dict[str, Any]:
        del jobs, total_jobs
        self._deprecated()

    def get_stats(self) -> Dict[str, Any]:
        return dict(self.stats)

    def get_results(self) -> List[JobResult]:
        return list(self.results)

    def get_successful_results(self) -> List[JobResult]:
        return [r for r in self.results if r.status == JobStatus.COMPLETED]

    def get_failed_results(self) -> List[JobResult]:
        return [r for r in self.results if r.status == JobStatus.FAILED]

    def print_stats(self) -> None:
        self._deprecated()

    def reset(self) -> None:
        self.stats = {}
        self.results = []
