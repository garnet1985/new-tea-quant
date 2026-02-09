"""
全局枚举和常量定义

包含整个应用程序级别的枚举类型和系统常量
"""
from enum import Enum

from core.utils.date.date_utils import DateUtils

class EntityType(Enum):
    """实体类型枚举(有时序的)"""
    STOCK_KLINE_DAILY = "stock_kline_daily"
    STOCK_KLINE_WEEKLY = "stock_kline_weekly"
    STOCK_KLINE_MONTHLY = "stock_kline_monthly"
    CORPORATE_FINANCE = "corporate_finance"
    GDP = "gdp"
    LPR = "lpr"
    SHIBOR = "shibor"
    PRICE_INDEXES = "price_indexes"
    TAG_SCENARIO = "tag_scenario"


class TermType(Enum):
    """周期类型枚举（主要用于 K 线 term 等业务语义）"""
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

class UpdateMode(Enum):
    """数据更新模式枚举"""
    INCREMENTAL = "incremental"
    REFRESH = "refresh"
    ROLLING = "rolling"

    @classmethod
    def from_string(cls, value: str) -> "UpdateMode":
        """从配置字符串解析为枚举。value 为 None 或无效时抛出 ValueError。"""
        if value is None:
            raise ValueError("renew type 未配置")
        v = str(value).strip().lower()
        for mode in cls:
            if mode.value == v:
                return mode
        raise ValueError(f"无效的 renew 模式: {value!r}，应为 incremental | refresh | rolling")


class SystemConstants:
    """系统级常量（不会频繁变更的）"""
    
    # 系统默认日期格式
    DATE_FORMAT = DateUtils.FMT_YYYYMMDD
    
    # 系统默认时间格式
    DATETIME_FORMAT = DateUtils.FMT_DATETIME

class IndicatorType(Enum):
    """技术指标类型枚举"""
    MOVING_AVERAGE = "moving_average"
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER_BANDS = "bollinger_bands"