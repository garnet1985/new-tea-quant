#!/usr/bin/env python3
"""
数据源相关枚举定义
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
