"""
Backtest Engine - 基础类型定义

回测执行管道类型（JobContext、JobReport、RunProgress 等）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class JobFailurePhase(str, Enum):
    """失败发生在哪一阶段。"""

    EXECUTE = "execute"
    REPORT = "report"


class ExecutionBackend(str, Enum):
    """执行后端：process | thread。"""

    PROCESS = "process"
    THREAD = "thread"


class ExecuteMode(str, Enum):
    """
    提交节奏（装填/load 由业务的 execute 或 run 前 payload 负责）。

    - QUEUE：有空位就 submit；完成 1 补 1
    - BATCH：每批 batch_size 个；批内并行、批间串行
    - ELASTIC：预留，动态 in-flight 门控（未实现）
    """

    QUEUE = "queue"
    BATCH = "batch"
    ELASTIC = "elastic"


class JobStatus(str, Enum):
    """任务执行结果状态（strategy 层 aggregate / progress 使用）。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Job:
    """任务单元：job_id + payload（业务自定 shape）。"""

    job_id: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RunCallbacks:
    """Optional hooks for a single BacktestEngine run (see api.yaml)."""

    on_result: Optional[Callable[["JobReport", RunProgress], None]] = None
    on_release: Optional[Callable[["JobReport"], None]] = None


@dataclass
class JobContext:
    """子进程 execute 收到的当前 job 作用域（由 Dispatcher 注入 job_id / task_name）。"""

    job_id: str
    payload: Dict[str, Any]
    task_name: str = ""


@dataclass
class JobReport:
    """Worker execute 返回的报告（pickle 友好，无 DB IO）。"""

    job_id: str
    success: bool
    data: Any = None
    error: Optional[str] = None


@dataclass
class JobResult:
    """BacktestEngine run 汇总后的单 job 结果（供 strategy aggregate 使用）。"""

    job_id: str
    status: JobStatus
    result: Any = None
    error: Optional[str] = None


@dataclass
class RunProgress:
    """单次 run 的进度快照，传给 on_result。"""

    finished: int
    total: int
    ok: int
    fail: int


@dataclass
class JobFailure:
    job_id: str
    phase: JobFailurePhase
    error: str


@dataclass
class DispatchResult:
    """一次 dispatch run 的汇总。"""

    total: int = 0
    completed: int = 0
    failed: int = 0
    failures: List[JobFailure] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    task_name: str = ""


ExecuteFn = Callable[[JobContext], Any]


__all__ = [
    "JobFailurePhase",
    "ExecutionBackend",
    "ExecuteMode",
    "JobStatus",
    "Job",
    "RunCallbacks",
    "JobContext",
    "JobReport",
    "JobResult",
    "RunProgress",
    "JobFailure",
    "DispatchResult",
    "ExecuteFn",
]
