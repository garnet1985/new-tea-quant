"""战役执行结果模型。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CellExecuteResult:
    """一格的缓存命中 / 跳过 / 补跑结果。"""

    index: int
    status: str
    version_id: Optional[str] = None
    execute_fp: Optional[str] = None
    env_fp: Optional[str] = None
    output_dir: Optional[str] = None
    reason: str = ""
