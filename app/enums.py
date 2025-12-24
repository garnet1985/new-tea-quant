"""
全局枚举和常量定义

包含整个应用程序级别的枚举类型和系统常量
"""
from enum import Enum


class KlineTerm(Enum):
    """K线周期枚举"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class AdjustType(Enum):
    """复权类型枚举"""
    NONE = "none"  # 不复权
    QFQ = "qfq"    # 前复权
    HFQ = "hfq"    # 后复权


class IndicatorType(Enum):
    """技术指标类型枚举"""
    MOVING_AVERAGE = "moving_average"
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER_BANDS = "bollinger_bands"


class DataUpdateMode(Enum):
    """数据更新模式枚举"""
    INCREMENTAL = "incremental"  # 增量更新
    FULL = "full"               # 全量更新
    MANUAL = "manual"           # 手动更新


class SystemConstants:
    """系统级常量（不会频繁变更的）"""
    
    # 系统默认日期格式
    DATE_FORMAT = "%Y%m%d"
    
    # 系统默认时间格式
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

