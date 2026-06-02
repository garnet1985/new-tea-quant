"""JobDispatcher 调度与执行配置。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from core.infra.job_dispatcher.types import ExecuteMode, ExecutionBackend


@dataclass
class JobDispatchSettings:
    """
    调度 + 执行后端配置。

    max_workers 解析由 WorkerProbe 负责（``"auto"`` 时按 CPU / reserve / cap）。
    """

    worker: ExecutionBackend = ExecutionBackend.PROCESS
    execute_mode: ExecuteMode = ExecuteMode.QUEUE
    max_workers: Union[str, int] = "auto"
    batch_size: int = 10
    """BATCH 模式每批 job 数。"""
    prefetch_ahead: int = 2
    ready_queue_limit: Optional[int] = None
    """默认 max_workers + prefetch_ahead。"""
    continue_on_failure: bool = True
    start_method: str = "spawn"
    reserve_cores: int = 2
    """auto 时为主进程保留的核心数。"""
    max_workers_cap: Optional[int] = None
    """auto 结果的上限（可选）。"""
