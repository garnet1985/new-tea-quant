"""JobPipeline 管道配置（线程/进程后端、QUEUE/BATCH 等）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Union

from core.infra.job_pipeline.types import ExecuteMode, ExecutionBackend

DuckdbProcessPoolScopeMode = Literal["auto", "on", "off"]


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
    max_parallel_jobs_cap: Optional[int] = None
    """``max_workers=auto`` 时 ProcessPool 同时 in-flight 的 job 数上限（可选）。"""
    duckdb_process_pool_scope: DuckdbProcessPoolScopeMode = "auto"
    """
    DuckDB + PROCESS 时主进程文件锁协作：

    - ``auto``：配置为 duckdb 且 worker=PROCESS 时自动 suspend/resume
    - ``on`` / ``off``：强制开启或关闭（见 ``core.infra.db.engines.duckdb.process_pool_scope``）
    """
    duckdb_data_mgr: Any = field(default=None, repr=False)
    """可选；默认用 DataManager 单例或临时实例。"""
    duckdb_resume_main_after_pool: bool = True
    """池结束后是否 resume 主库；Tag spill 收尾写库前可设为 False。"""
    worker_profile: str = "default"
    """``worker.json`` → ``job_pipeline`` profile 名（``max_workers=auto`` 时使用）。"""
