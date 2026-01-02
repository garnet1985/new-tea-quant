"""
Tag 系统枚举定义

包含 Tag 配置中使用的所有枚举类型，用于减少用户输入错误。
"""
from enum import Enum


class KlineTerm(Enum):
    """K线周期枚举"""
    DAILY = "daily"      # 日线
    WEEKLY = "weekly"    # 周线
    MONTHLY = "monthly"  # 月线

class FileName(Enum):
    """文件名枚举"""
    SETTINGS = "settings.py"
    TAG_WORKER = "tag_worker.py"

class UpdateMode(Enum):
    """更新模式枚举"""
    INCREMENTAL = "incremental"  # 增量更新
    REFRESH = "refresh"          # 全量刷新


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