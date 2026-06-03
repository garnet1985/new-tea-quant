"""JobPipeline 管道配置（线程/进程后端、QUEUE/BATCH 等）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from core.infra.job_pipeline.types import ExecuteMode, ExecutionBackend


@dataclass
class JobPipelineSettings:
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
    reserve_cores: int = 1
    """auto 时为 OS + 主进程（stage/report）保留的逻辑核数。"""
    max_workers_cap: Optional[int] = None
    """auto 结果的上限（可选）。"""
