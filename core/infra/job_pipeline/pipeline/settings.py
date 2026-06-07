"""JobPipeline 管道配置（线程/进程后端、QUEUE/BATCH 等）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Union

from core.infra.job_pipeline.types import ExecuteMode, ExecutionBackend

DuckdbProcessPoolScopeMode = Literal["auto", "on", "off"]


@dataclass
class JobPipelineSettings:
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
    duckdb_process_pool_scope: DuckdbProcessPoolScopeMode = "auto"
    duckdb_data_mgr: Any = field(default=None, repr=False)
    duckdb_resume_main_after_pool: bool = True
    worker_profile: str = "default"
