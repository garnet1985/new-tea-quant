"""
JobDispatcher 类型定义。

jobs[] → executor(JobContext) → on_result
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


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
    主进程装填 + 提交节奏。

    - QUEUE：有空位就 submit；完成 1 补 1
    - BATCH：每批 batch_size 个；批内并行、批间串行
    - ELASTIC：预留，动态调池（未实现）
    """

    QUEUE = "queue"
    BATCH = "batch"
    ELASTIC = "elastic"


@dataclass(frozen=True)
class Job:
    """任务单元：job_id + payload（业务自定 shape）。"""

    job_id: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JobContext:
    """子进程 execute 收到的当前 job 作用域（由 Dispatcher 注入 job_id / run_name）。"""

    job_id: str
    payload: Dict[str, Any]
    run_name: str = ""


@dataclass
class JobReport:
    """Worker execute 返回的报告（pickle 友好，无 DB IO）。"""

    job_id: str
    success: bool
    data: Any = None
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
    run_name: str = ""
