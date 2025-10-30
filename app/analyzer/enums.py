#!/usr/bin/env python3
"""
分析器相关枚举定义

只包含真正属于analyzer职责范围的枚举：
- 投资结果相关
- 技术指标类型
- 验证结果
- 数据处理模式
"""
from enum import Enum


class InvestmentResult(Enum):
    """投资结果枚举"""
    WIN = "win"
    LOSS = "loss"
    OPEN = "open"


class IndicatorType(Enum):
    """技术指标类型枚举"""
    MOVING_AVERAGE = "moving_average"
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER_BANDS = "bollinger_bands"


class ValidationResult(Enum):
    """验证结果枚举"""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


class DataProcessingMode(Enum):
    """数据处理模式枚举"""
    REALTIME = "realtime"      # 实时处理
    BATCH = "batch"           # 批量处理


class MarketType(Enum):
    """市场类型枚举"""
    BULL = "bull"
    BEAR = "bear"
    STABLE = "stable"