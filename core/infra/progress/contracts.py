"""进度快照的字段。"""
from __future__ import annotations

from typing import TypedDict


class ProgressSnapshot(TypedDict):
    """当前任务进度。显示层用 step 与 sub 自己算比例。"""

    job: str
    source: str
    step: int
    step_total: int
    sub: int
    sub_total: int
    updated_at: int
