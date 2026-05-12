"""工作台步骤执行管理 — 类型与协议占位（实现见 planning / execution）。"""

from __future__ import annotations

from typing import Any, Callable, Protocol, Tuple

# 与 ``execution_manager.workbench_resolve.normalize_step`` 合法集一致：enum / price / capital。
WorkbenchSubstep = str
PlannedSubstep = Tuple[WorkbenchSubstep, bool]


class ProgressSink(Protocol):
    """由 BFF / CLI 注入：执行管理内核只调此协议，不直接写 Flask 或终端。"""

    def on_overall_pct(self, pct: float) -> None:
        pass

    def on_substep_start(self, substep: str, index: int, total: int) -> None:
        pass

    def on_flow_progress(self, substep: str, flow_pct: float) -> None:
        pass


ProgressCallback = Callable[[float], None]

__all__ = [
    "PlannedSubstep",
    "ProgressCallback",
    "ProgressSink",
    "WorkbenchSubstep",
    "WorkbenchExecutionResult",
]


class WorkbenchExecutionResult:
    """同步执行结束：快照 id、可选的最后子步骤产物（供 CLI 展示）。"""

    snapshot_id: int
    error: Any
    last_payload: Any
    last_used_db_cache: Any

    def __init__(
        self,
        *,
        snapshot_id: int = 0,
        error: Any = None,
        last_payload: Any = None,
        last_used_db_cache: Any = None,
    ) -> None:
        self.snapshot_id = snapshot_id
        self.error = error
        self.last_payload = last_payload
        self.last_used_db_cache = last_used_db_cache
