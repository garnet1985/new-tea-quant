"""
Backtest Scheduler - General Settings

JobPipeline通用配置（线程/进程后端、QUEUE/BATCH等），不包含任何DB特殊配置。

设计原则：
- General settings：只包含ProcessPoolExecutor/ThreadPoolExecutor的基本配置
- 不包含DuckDB或其他DB的特殊配置
- 未来DuckDB分支可以继承并添加特有配置
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from .types import ExecuteMode, ExecutionBackend


@dataclass
class JobPipelineSettings:
    """General JobPipeline配置（不包含DB特殊配置）。"""

    worker: ExecutionBackend = ExecutionBackend.PROCESS
    execute_mode: ExecuteMode = ExecuteMode.QUEUE
    max_workers: Union[str, int] = "auto"
    batch_size: int = 10
    prefetch_ahead: int = 2
    ready_queue_limit: Optional[int] = None
    continue_on_failure: bool = True
    start_method: str = "spawn"
    reserve_cores: int = 1
    max_parallel_jobs_cap: Optional[int] = None
    worker_profile: str = "default"


__all__ = ["JobPipelineSettings"]