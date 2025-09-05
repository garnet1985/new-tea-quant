#!/usr/bin/env python3
"""
HistoricLow策略枚举定义
"""
from enum import Enum


class InvestmentResult(Enum):
    """投资结果枚举"""
    WIN = 'win'
    LOSS = 'loss'
    OPEN = 'open'
