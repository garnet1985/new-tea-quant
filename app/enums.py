"""
全局枚举和常量定义

包含整个应用程序级别的枚举类型和系统常量
"""
from enum import Enum
from token import LPAR

class EntityType(Enum):
    """实体类型枚举"""
    STOCK_KLINE_DAILY = "stock_kline_daily"
    STOCK_KLINE_WEEKLY = "stock_kline_weekly"
    STOCK_KLINE_MONTHLY = "stock_kline_monthly"
    CORPORATE_FINANCE = "corporate_finance"
    GDP = "gdp"
    LPR = "lpr"
    SHIBOR = "shibor"
    PRICE_INDEXES = "price_indexes"


class TermType(Enum):
    """周期类型枚举"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

# TODO: replace with TermType
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

class UpdateMode(Enum):
    """数据更新模式枚举"""
    INCREMENTAL = "incremental"  
    REFRESH = "refresh"               
    ROLLING = "rolling"           

class SystemConstants:
    """系统级常量（不会频繁变更的）"""
    
    # 系统默认日期格式
    DATE_FORMAT = "%Y%m%d"
    
    # 系统默认时间格式
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class IndicatorType(Enum):
    """技术指标类型枚举"""
    MOVING_AVERAGE = "moving_average"
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER_BANDS = "bollinger_bands"