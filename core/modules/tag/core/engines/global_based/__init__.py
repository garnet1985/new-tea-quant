"""global 时序 Tag：轻量主进程推进器（不走 BacktestEngine）。

实体池为哨兵 ``GLOBAL_ENTITY_ID``；钩子复用 ``calculate_tag``。
"""

from .constants import GLOBAL_ENTITY_ID
from .data_loader import TagGlobalDataLoader
from .pipeline import TagGlobalPipeline

__all__ = [
    "GLOBAL_ENTITY_ID",
    "TagGlobalDataLoader",
    "TagGlobalPipeline",
]
