"""进度节点的字段。根节点和每一层 steps 使用同一种结构。"""
from __future__ import annotations

from typing import List, TypedDict


class ProgressNode(TypedDict):
    """一份进度。有子节点时 ratio 来自子节点，否则来自 done / total。"""

    id: str
    job: str
    status: str
    source: str
    label: str
    detail: str
    weight: float
    done: int
    total: int
    ratio: float
    started_at: int
    updated_at: int
    steps: List["ProgressNode"]
