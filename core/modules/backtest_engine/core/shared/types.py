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
    """调度提交单元：job_id + payload（业务自定 shape）。"""

    job_id: str
    payload: Dict[str, Any] = field(default_factory=dict)


# Task 侧钩子类型（寄生主体见 RunCallbacks 文档）
TaskStartFn = Callable[["JobContext"], Any]
#: 可返回 Optional[dict]，并入该 task 结果；失败路径返回值可忽略。
TaskCompleteFn = Callable[["JobContext"], Any]
TickFn = Callable[["JobContext", str, int], None]
ExecuteFn = Callable[["JobContext"], Any]
# slice_based 探针/预读装数（由调用方注入；BE 不依赖 strategy）
LoadPerEntityWindowFn = Callable[..., Dict[str, Any]]


@dataclass
class RunCallbacks:
    """BacktestEngine run 生命周期钩子（entity / slice 共用）。

    Task = run 内的 partial work（不是整个 run）。寄生主体：

    - ``entity_based``：一个 worker 进程内的一次 ProcessPool 提交
    - ``slice_based``：一片正式日历 slice 的 compute

    BE 只提供时间点；钩子名不暗示业务动作（settle / flush / 进度等）。
    业务在钩子内自行安排。

    调用顺序（概念）：

    - 主：``on_before_all_tasks_start``
    - task 侧：``on_task_start`` → ``on_tick`` × N → ``on_task_complete``
    - 主（仅跨进程收回结果时）：``on_receive_task_result``
    - 主：``on_after_all_tasks_complete``

    ``on_receive_task_result``：entity 主进程收 worker 结果时调用；
    slice 同进程跑 task 时默认不调用。

    slice_based：须注入 ``load_per_entity_window``（探针 + SliceReaderPool）；
    entity_based 可忽略。
    """

    # ── 主进程（run 级）──
    on_before_all_tasks_start: Optional[Callable[[Any, List[Any]], None]] = None
    on_after_all_tasks_complete: Optional[Callable[[List["JobReport"]], None]] = None
    #: 主进程收到跨进程 task 结果后（entity）；slice 默认不调。
    on_receive_task_result: Optional[Callable[["JobReport", "RunProgress"], None]] = None

    # ── Task 侧（寄生主体内）──
    on_task_start: Optional[TaskStartFn] = None
    on_task_complete: Optional[TaskCompleteFn] = None

    # ── 日历推进（task 内）──
    on_tick: Optional[TickFn] = None

    # ── slice 数据面（调用方提供；非生命周期）──
    load_per_entity_window: Optional[LoadPerEntityWindowFn] = None


@dataclass
class JobContext:
    """当前 task 作用域（由执行器注入 job_id / task_name）。"""

    job_id: str
    payload: Dict[str, Any]
    task_name: str = ""
    init: Any = None


@dataclass
class JobReport:
    """Worker / task 返回的报告（pickle 友好，无 DB IO）。"""

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
    """主进程侧已完成 task 计数快照（传给 on_receive_task_result）。"""

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
    "TaskStartFn",
    "TaskCompleteFn",
    "TickFn",
    "LoadPerEntityWindowFn",
]
