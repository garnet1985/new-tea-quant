"""跨模块契约：长任务租约异常与常量。

推荐::

    from core.infra.task_guard import TaskGuard
    from core.infra.task_guard.contracts import TaskLeaseBusyError

``TaskLease`` 也可从此模块导入（懒加载实现类）。
"""

from __future__ import annotations

from typing import Any

VALID_KINDS = frozenset(
    {"tag_run", "strategy_scan", "strategy_run", "data_renew"}
)


class TaskLeaseBusyError(Exception):
    """``acquire`` 失败：已有长任务持有全局互斥租约。"""

    def __init__(self, active: dict):
        self.active = dict(active)
        kind = active.get("kind") or "unknown"
        super().__init__(f"task busy: kind={kind}")


def __getattr__(name: str) -> Any:
    if name == "TaskLease":
        from core.infra.task_guard.core.lease.task_lease import TaskLease

        return TaskLease
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "VALID_KINDS",
    "TaskLeaseBusyError",
    "TaskLease",
]
