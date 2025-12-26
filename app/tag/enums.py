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


class UpdateMode(Enum):
    """更新模式枚举"""
    INCREMENTAL = "incremental"  # 增量更新
    REFRESH = "refresh"          # 全量刷新


class VersionChangeAction(Enum):
    """版本变更时的行为枚举"""
    NEW_TAG = "new_tag"        # 创建新 tag（保留旧数据）
    FULL_REFRESH = "full_refresh"  # 全量刷新（覆盖旧数据）


class SupportedDataSource(Enum):
    """支持的数据源枚举"""
    KLINE = "kline"
    CORPORATE_FINANCE = "corporate_finance"