"""Tag 模块枚举。

消费者: tag_settings, discovery, engines
"""

from __future__ import annotations

from enum import Enum


class FileName(Enum):
    SETTINGS = "settings.py"
    TAG = "tag.py"


class TagUpdateMode(Enum):
    INCREMENTAL = "incremental"
    REFRESH = "refresh"


class TagExecutionMode(Enum):
    """与 strategy / BacktestEngine 对齐。"""

    ENTITY_BASED = "entity_based"
    SLICE_BASED = "slice_based"


__all__ = [
    "FileName",
    "TagUpdateMode",
    "TagExecutionMode",
]
