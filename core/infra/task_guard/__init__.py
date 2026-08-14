"""
长任务互斥守卫（``infra.task_guard``）。

包根仅导出 ``TaskGuard``；类型见 ``contracts``。
"""

from .task_guard import TaskGuard

__all__ = ["TaskGuard"]
