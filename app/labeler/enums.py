#!/usr/bin/env python3
"""
标签器相关枚举定义
"""
from enum import Enum


class LabelCategory(Enum):
    """标签分类枚举"""
    MARKET_CAP = "market_cap"
    INDUSTRY = "industry"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    FINANCIAL = "financial"
