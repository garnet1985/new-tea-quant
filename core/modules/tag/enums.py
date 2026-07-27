"""
Tag 系统枚举定义（旧路径）。

MIGRATED → ``core.modules.tag.core.enums``

AUDIT: 待旧 engines / TagManager / ScenarioModel 切到 ``tag.core.enums`` 后删除本文件。
新代码请::

    from core.modules.tag.core.enums import (
        FileName,
        TagUpdateMode,
        TagTargetType,
        TagExecutionMode,
    )
"""
from enum import Enum

class FileName(Enum):
    """文件名枚举"""
    SETTINGS = "settings.py"
    TAG_WORKER = "tag_worker.py"

class TagUpdateMode(Enum):
    """Tag 系统更新模式枚举（只支持增量更新和全量刷新）"""
    INCREMENTAL = "incremental"  # 增量更新
    REFRESH = "refresh"          # 全量刷新


class TagTargetType(Enum):
    """Tag 目标类型：实体标签 or 全局标签。"""

    ENTITY_BASED = "entity_based"
    GENERAL = "general"


class TagExecutionMode(Enum):
    """Tag 执行模式：与 strategy / BacktestEngine 对齐（entity_based | slice_based）。"""

    ENTITY_BASED = "entity_based"
    SLICE_BASED = "slice_based"


# 已废弃：版本管理相关枚举已移除
# class VersionChangeAction(Enum):
#     """版本变更时的行为枚举（Scenario 级别）"""
#     REFRESH_SCENARIO = "refresh_scenario"
#     NEW_SCENARIO = "new_scenario"

# class EnsureMetaAction(Enum):
#     """确保元信息动作枚举（内部使用）"""
#     NO_CHANGE = "no_change"
#     META_UPDATE = "meta_update"
#     NEW_SCENARIO = "new_scenario"
#     ROLLBACK = "rollback"


class SupportedDataSource(Enum):
    """支持的数据源枚举"""
    KLINE = "kline"
    CORPORATE_FINANCE = "corporate_finance"