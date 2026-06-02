"""
JobDispatcher 类型定义。

JobShell → on_stage_job → StagedJob → Worker(execute) → JobReport → on_report
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class JobFailurePhase(str, Enum):
    """失败发生在哪一阶段。"""

    STAGE = "stage"
    EXECUTE = "execute"
    REPORT = "report"


class ExecutionBackend(str, Enum):
    """
    执行后端类型（仅用于 factory 选 infra.worker 实现）。

    JobDispatcher 本身无 process/thread mode；通过注入 JobExecutor 区分。
    """

    PROCESS = "process"
    THREAD = "thread"


@dataclass(frozen=True)
class DataRef:
    """
    大数据注入引用（避免 pickle 整表）。

    由 on_stage_job 写入，Worker 侧按 ref 加载（如 parquet 路径、shm 名）。
    """

    slot: str
    uri: str
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class JobShell:
    """
    轻量任务空壳（无大表数据）。

    由业务层 build（如 TagManager._build_jobs）产出。
    """

    job_id: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StagedJob:
    """
    装填后的可运行任务（主进程 on_stage_job 产出）。

    submit 给 Worker 时使用 payload；data_refs 可选。
    """

    job_id: str
    shell: JobShell
    payload: Dict[str, Any] = field(default_factory=dict)
    data_refs: List[DataRef] = field(default_factory=list)


@dataclass
class JobReport:
    """Worker execute 返回的报告（pickle 友好，无 DB IO）。"""

    job_id: str
    success: bool
    data: Any = None
    error: Optional[str] = None


@dataclass
class JobFailure:
    job_id: str
    phase: JobFailurePhase
    error: str


@dataclass
class DispatchConfig:
    """
    Dispatcher 调度配置（不含并行度）。

    max_workers 由注入的 JobExecutor 提供；ready 窗口见 prefetch_ahead。

    填池策略（fill_strategy）见 ARCHITECTURE.md §6；当前仅 QUEUE 已实现。
    """

    prefetch_ahead: int = 2
    ready_queue_limit: Optional[int] = None
    """默认 executor.max_workers + prefetch_ahead，实现阶段计算。"""
    spill_dir: Optional[str] = None
    """可选 spill 根目录；Tag 当前 inline inject，profiling 后再决定是否启用。"""
    # --- 以下字段为规划中的填池策略，尚未在 JobDispatcher.run 中实现 ---
    fill_strategy: str = "queue"
    """``queue`` | ``batch`` | ``chunk``，见 FillStrategy。"""
    batch_size: Optional[int] = None
    """BATCH：每批 job 数；批间串行，批内并行。"""
    chunk_size: Optional[int] = None
    """CHUNK：累计完成 chunk_size 个后再 stage/submit 下一组（降低 IO / pickle 频率）。"""


class FillStrategy(str, Enum):
    """
    主进程装填 + 提交节奏（规划）。

    - QUEUE：池有空位就 stage/submit（当前默认，近似旧 ProcessWorker QUEUE）
    - BATCH：每批 batch_size 个，批间串行、批内并行（近似旧 BATCH）
    - CHUNK：in-flight 上限不变；累计完成 chunk_size 个后再批量 stage 下一组
    """

    QUEUE = "queue"
    BATCH = "batch"
    CHUNK = "chunk"


@dataclass
class DispatchResult:
    """一次 dispatch run 的汇总（不含业务数据本身）。"""

    total: int = 0
    completed: int = 0
    failed: int = 0
    failures: List[JobFailure] = field(default_factory=list)
    elapsed_seconds: float = 0.0
