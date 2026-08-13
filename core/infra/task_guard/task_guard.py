"""TaskGuard 门面 — 长任务忙闲查询与互斥租约。

方法内懒导入，避免包 import 时拉起重链。
"""

from __future__ import annotations

from typing import Any, Optional

from .contracts import VALID_KINDS, TaskLeaseBusyError


class TypesNamespace:
    """与 ``contracts`` 同源的类型 / 常量挂载点。"""

    VALID_KINDS = VALID_KINDS
    TaskLeaseBusyError = TaskLeaseBusyError

    def __getattr__(self, name: str) -> Any:
        if name == "TaskLease":
            from core.infra.task_guard.core.lease.task_lease import TaskLease

            return TaskLease
        raise AttributeError(f"{type(self).__name__!r} has no attribute {name!r}")


class TaskGuard:
    """长任务互斥守卫：同时只允许一个全局长任务占用资源。"""

    types = TypesNamespace()

    @staticmethod
    def read_status() -> dict:
        from core.infra.task_guard.core.lease.task_lease import TaskLease

        return TaskLease.read_status()

    @staticmethod
    def lease(
        *,
        kind: str,
        job_id: str,
        resource_key: str = "",
        label: str = "",
        domains: Optional[list] = None,
    ):
        """构造 ``TaskLease`` 上下文管理器。"""
        from core.infra.task_guard.core.lease.task_lease import TaskLease

        return TaskLease(
            kind=kind,
            job_id=job_id,
            resource_key=resource_key,
            label=label,
            domains=domains,
        )


__all__ = ["TaskGuard"]
