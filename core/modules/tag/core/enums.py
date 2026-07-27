"""Tag 模块枚举（新 core 包）。

消费者: tag_settings, discovery, engines
"""

from __future__ import annotations

from enum import Enum


class FileName(Enum):
    SETTINGS = "settings.py"
    TAG_WORKER = "tag.py"


class TagUpdateMode(Enum):
    INCREMENTAL = "incremental"
    REFRESH = "refresh"


class TagTargetType(Enum):
    ENTITY_BASED = "entity_based"
    GENERAL = "general"


class TagExecutionMode(Enum):
    """与 strategy / BacktestEngine 对齐。"""

    ENTITY_BASED = "entity_based"
    SLICE_BASED = "slice_based"


__all__ = [
    "FileName",
    "TagUpdateMode",
    "TagTargetType",
    "TagExecutionMode",
]
